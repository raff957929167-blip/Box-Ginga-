"""Workflows de prospecção da Ginga Studio.

ginga-lead-radar: varre a web em busca de leads (agente com web search).
ginga-lead-qualifier: qualifica leads brutos e gera mensagem de abordagem.
"""

import json
import re
from datetime import timedelta
from typing import Any

from pydantic import BaseModel, Field

from mistralai.workflows import Depends, activity, workflow
from mistralai.workflows.client import get_mistral_client

MODELO = "mistral-medium-latest"

OFERTA = (
    "Ginga Studio: agência angolana de gestão de redes sociais. "
    "Pacote completo: identidade visual, peças gráficas, SEO social, "
    "planejamento e criação de postagens, posicionamento de marca e chatbot 24/7. "
    "Preço em Angola: 50.000 Kz/mês."
)

ICP = (
    "Cliente ideal: donos e diretores de PMEs com 30+ anos, em Angola "
    "(prioridade Luanda e área metropolitana), com presença digital fraca, "
    "inativa ou inexistente no Instagram/Facebook. Setores: restaurantes, "
    "ginásios, clínicas, escolas, imobiliárias, salões e barbearias, "
    "escritórios de advocacia, retalho, eventos, logística, viagens e "
    "negócios recém-abertos. Nos mercados externos, priorizar países "
    "lusófonos (Moçambique, Cabo Verde, São Tomé e Príncipe, Guiné-Bissau, "
    "Portugal, Brasil) e negócios lusófonos no resto do mundo."
)


@activity
async def qualify_lead(
    lead: dict[str, Any],
    client: Any = Depends(get_mistral_client),
) -> dict[str, Any]:
    """Avalia um lead contra o perfil ideal e gera a primeira abordagem.

    Args:
        lead: Dados públicos do lead (nome, setor, local, contactos, sinal).
        client: Cliente Mistral injetado pelo SDK.
    """
    system = (
        "Você é o qualificador de leads da Ginga Studio. Avalie o lead contra "
        "o perfil de cliente ideal e a oferta. Responda APENAS com um objeto "
        "JSON válido, sem texto extra, com as chaves: score (inteiro de 0 a "
        "100), enquadra (booleano), motivo (1 a 2 frases), angulo (ângulo de "
        "abordagem para a primeira conversa) e mensagem_whatsapp (mensagem de "
        "primeira abordagem pronta para enviar, curta, em português, informal "
        "e profissional, focada no benefício principal para o negócio dele)."
    )
    user = json.dumps(
        {"oferta": OFERTA, "perfil_ideal": ICP, "lead": lead},
        ensure_ascii=False,
    )
    response = await client.chat.complete_async(
        model=MODELO,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "score": 0,
            "enquadra": False,
            "motivo": "resposta inválida do modelo",
            "angulo": "",
            "mensagem_whatsapp": "",
        }
    data["lead"] = lead
    return data


@activity
async def scan_market(params: dict[str, Any]) -> dict[str, Any]:
    """Roda o agente de prospecção com busca na web e devolve leads.

    Args:
        params: mercado, setor e quantidade de leads desejada.
    """
    from mistralai.client.models import TextChunk, WebSearchTool
    from mistralai.workflows.plugins.mistralai import Agent, RemoteSession, Runner

    agente = Agent(
        model=MODELO,
        name="ginga-lead-radar",
        description="Agente de prospecção B2B da Ginga Studio com busca na web",
        instructions=(
            "Você é um agente de prospecção B2B da Ginga Studio. Use a busca "
            "na web para encontrar pequenas e médias empresas reais do "
            "mercado indicado que tenham presença digital fraca, inativa ou "
            "inexistente nas redes sociais. Priorize negócios recém-abertos. "
            "Para cada empresa, colete nome, setor, localização, contactos "
            "públicos (telefone, WhatsApp, email ou Instagram) e o sinal de "
            "presença digital fraca. Use apenas fontes públicas. Não invente "
            "dados: campo não encontrado preencha com null. Ao final, "
            "responda APENAS com um objeto JSON válido no formato: "
            '{"leads": [{"nome": str, "setor": str, "local": str, '
            '"contacto": str, "instagram": str, "sinal_presenca_fraca": str, '
            '"fonte": str}]} sem nenhum texto fora do JSON.'
        ),
        tools=[WebSearchTool()],
    )

    pergunta = (
        "Encontre {quantidade} leads para a Ginga Studio. "
        "Mercado: {mercado}. Setor: {setor}. "
        "Contexto da oferta: {oferta} Perfil ideal de cliente: {icp}"
    ).format(
        quantidade=params.get("quantidade", 10),
        mercado=params.get("mercado", "Angola"),
        setor=params.get("setor", "todos os setores"),
        oferta=OFERTA,
        icp=ICP,
    )

    outputs = await Runner.run(
        agent=agente,
        inputs=pergunta,
        session=RemoteSession(),
        max_turns=25,
    )
    texto = "\n".join(
        o.text for o in outputs if isinstance(o, TextChunk)
    )
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {"leads": [], "observacao": texto[:4000]}


class RadarInput(BaseModel):
    mercado: str = "Angola, prioridade Luanda e área metropolitana"
    setor: str = "todos os setores"
    quantidade: int = Field(default=10, ge=3, le=20)


class LeadsInput(BaseModel):
    leads: list[dict[str, Any]] = Field(default_factory=list)


@workflow.define(name="ginga-lead-radar")
class GingaLeadRadar:
    @workflow.run
    async def run(self, input: RadarInput) -> dict[str, Any]:
        resultado = await workflow.execute_activity(
            scan_market,
            input.model_dump(),
            start_to_close_timeout=timedelta(minutes=15),
        )
        leads = resultado.get("leads", []) if isinstance(resultado, dict) else []
        observacao = resultado.get("observacao", "") if isinstance(resultado, dict) else ""
        return {
            "total_encontrados": len(leads),
            "leads": leads,
            "observacao": observacao,
        }


@workflow.define(name="ginga-lead-qualifier")
class GingaLeadQualifier:
    @workflow.run
    async def run(self, input: LeadsInput) -> dict[str, Any]:
        qualificados = []
        for lead in input.leads:
            try:
                resultado = await workflow.execute_activity(
                    qualify_lead,
                    lead,
                    start_to_close_timeout=timedelta(minutes=2),
                )
            except Exception:
                resultado = None
            if resultado and resultado.get("enquadra"):
                qualificados.append(resultado)
        qualificados.sort(key=lambda r: r.get("score", 0), reverse=True)
        return {
            "total_recebidos": len(input.leads),
            "total_qualificados": len(qualificados),
            "leads_qualificados": qualificados,
        }
