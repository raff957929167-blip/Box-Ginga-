# Ginga Studio - Workflow de Leads

Workflows Mistral para prospecção de clientes da Ginga Studio (gestão de redes sociais, 50.000 Kz/mês em Angola).

## Workflows

- ginga-lead-radar: agente com busca na web que encontra empresas com presença digital fraca. Entrada: {"mercado": "Angola, prioridade Luanda", "setor": "restaurantes", "quantidade": 10}
- ginga-lead-qualifier: pontua cada lead contra o perfil ideal e gera mensagem de abordagem pronta. Entrada: {"leads": [{"nome": "...", "setor": "...", "local": "...", "contacto": "...", "sinal_presenca_fraca": "..."}]}

Prioridade de mercados: Angola (Luanda primeiro), depois lusófonos (Moçambique, Cabo Verde, São Tomé e Príncipe, Guiné-Bissau, Portugal, Brasil), depois o resto do mundo.

Nunca comite API keys. O deploy gerenciado injeta a autenticação de service account.
