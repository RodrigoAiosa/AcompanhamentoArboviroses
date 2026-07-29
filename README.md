# 🦟 Painel de Acompanhamento de Arboviroses (Dengue, Zika, Chikungunya)

Painel interativo para acompanhar o nível de alerta e a evolução de casos de
dengue, zika e chikungunya em qualquer município do Brasil, usando dados
oficiais e abertos.

## Por que esse projeto existe

O Brasil enfrenta surtos recorrentes de arboviroses, mas a informação sobre
risco epidemiológico raramente chega de forma clara ao cidadão comum. Os
dados existem (a Fiocruz mantém um sistema de vigilância robusto), mas estão
espalhados em relatórios técnicos. Este painel traduz esses dados em uma
visualização simples: nível de alerta, série histórica e comparação entre anos.

## Fontes de dados

- **[InfoDengue](https://info.dengue.mat.br)** (Fiocruz / EMAp-FGV) — série
  histórica semanal de casos e nível de alerta por município.
- **[API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades)**
  — lista de municípios e seus códigos geográficos (geocode).

## Funcionalidades

- 🔎 Busca de município por nome (sem precisar saber o código IBGE)
- 🚦 Nível de alerta atual (verde / amarelo / laranja / vermelho)
- 📈 Gráfico da série histórica de casos, com intervalo de confiança
- 📊 Comparação de casos totais por ano
- 🦠 Suporte a dengue, zika e chikungunya
- 📋 Visualização dos dados brutos para quem quiser analisar por conta própria

## Como rodar localmente

```bash
# 1. Clone o repositório
git clone https://github.com/SEU_USUARIO/painel-dengue-brasil.git
cd painel-dengue-brasil

# 2. Crie um ambiente virtual (opcional, mas recomendado)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Rode o app
streamlit run app.py
```

O app abrirá automaticamente em `http://localhost:8501`.

## Deploy gratuito (Streamlit Community Cloud)

1. Suba este repositório para o GitHub.
2. Acesse [share.streamlit.io](https://share.streamlit.io).
3. Conecte sua conta do GitHub e selecione o repositório.
4. Aponte para o arquivo `app.py`.
5. Deploy automático — pronto, você tem uma URL pública.

## Estrutura do projeto

```
painel-dengue-brasil/
├── app.py                 # App principal do Streamlit
├── requirements.txt        # Dependências
├── utils/
│   ├── ibge.py             # Busca de municípios/geocodes via API do IBGE
│   └── infodengue.py       # Consulta e tratamento de dados do InfoDengue
└── README.md
```

## Próximos passos (ideias de expansão)

- [ ] Mapa coroplético do Brasil colorido por nível de alerta (usando `plotly` + geojson de municípios/estados)
- [ ] Comparação entre múltiplos municípios ao mesmo tempo
- [ ] Alertas por e-mail/Telegram quando o nível de risco de uma cidade salvar mudar
- [ ] Exportação dos dados filtrados em CSV/Excel
- [ ] Correlação com dados climáticos (temperatura/chuva) também disponíveis na API do InfoDengue

## Limitações conhecidas

- A API do InfoDengue considera apenas casos **notificados** via SINAN; subnotificação
  é uma limitação inerente aos próprios dados, não do painel.
- Dados das semanas mais recentes são preliminares e sujeitos a atualização
  (conforme aviso oficial da própria API).

## Licença

Este projeto é livre para uso educacional e não comercial. Os dados utilizados
pertencem às respectivas instituições (Fiocruz/EMAp-FGV e IBGE) e seguem as
licenças de dados abertos de cada uma.
