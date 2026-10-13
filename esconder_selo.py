"""Esconde os controles do Streamlit Cloud: Deploy, menu, Share, favorito,
editar, GitHub, "Manage app", selo "Hosted with Streamlit" e foto do dono.

Mesma técnica do API Atlas e do site rodrigoaiosa.streamlit.app:
- CSS cobre os nomes de classe conhecidos;
- um script reforça, achando os itens pelo texto ou pelo link para
  streamlit.io/cloud, inclusive quando o Streamlit Cloud muda as classes.

O cabeçalho continua visível, porque nele fica o botão de abrir o menu lateral.
Chame esconder_selo_streamlit() logo depois de st.set_page_config().
"""

import streamlit as st

_CSS = """<style>
[data-testid="stToolbarActions"],
[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"],
#MainMenu,
.stAppDeployButton,
.stDeployButton,
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="manage-app-button"],
[data-testid="stManageAppButton"],
[class*="viewerBadge"],
[class*="_terminalButton_"],
[class*="_container_gzau3_"],
[class*="profileContainer"],
[class*="profilePreview"],
[class*="hostedWith"],
a[href*="streamlit.io/cloud"],
div:has(> a[href*="streamlit.io/cloud"]) {
    display: none !important;
    visibility: hidden !important;
}
/* O iframe de 1px que só roda o script abaixo fica fora do layout. */
.st-key-esconder_selo {
    position: absolute !important; width: 1px !important; height: 1px !important;
    margin: 0 !important; padding: 0 !important; overflow: hidden !important;
    opacity: 0 !important; pointer-events: none !important;
}
</style>"""

_SCRIPT = """<script>
(function() {
    // Documentos que tentamos limpar: o do app (parent) e, se o navegador
    // permitir (mesma origem), o da página que o envolve (top).
    const docs = [];
    [window.parent, window.top].forEach(w => {
        try { if (w && w.document && !docs.some(d => d.w === w)) docs.push({w: w, doc: w.document}); } catch (e) {}
    });
    const TEXTOS = /^(hosted with streamlit|manage app)$/i;
    function esconder({w, doc}) {
        try {
            const alvos = new Set();
            doc.querySelectorAll('a[href*="streamlit.io/cloud"]').forEach(a => alvos.add(a));
            doc.querySelectorAll('body *').forEach(el => {
                if (el.children.length === 0 && TEXTOS.test((el.textContent || '').trim())
                    && (el.textContent || '').length < 40) alvos.add(el);
            });
            // foto de perfil do dono (avatar) fixa no canto inferior direito
            doc.querySelectorAll('img').forEach(img => {
                const r = img.getBoundingClientRect();
                const vw = w.innerWidth, vh = w.innerHeight;
                if (r.width > 0 && r.width <= 90 && r.height <= 90 &&
                    r.right > vw - 170 && r.bottom > vh - 130) {
                    let n = img, fixo = false;
                    for (let i = 0; i < 8 && n && n !== doc.body; i++, n = n.parentElement) {
                        if (w.getComputedStyle(n).position === 'fixed') { fixo = true; break; }
                    }
                    if (fixo) alvos.add(img);
                }
            });
            alvos.forEach(el => {
                // sobe até o contêiner fixo do selo/botão, sem passar do <body>
                let alvo = el, n = el;
                for (let i = 0; i < 8 && n && n !== doc.body; i++, n = n.parentElement) {
                    if (w.getComputedStyle(n).position === 'fixed') { alvo = n; break; }
                }
                alvo.style.setProperty('display', 'none', 'important');
            });
        } catch (e) {}
    }
    docs.forEach(d => {
        try { new MutationObserver(() => esconder(d)).observe(d.doc.body, { childList: true, subtree: true }); } catch (e) {}
        esconder(d);
    });
})();
</script>"""


def esconder_selo_streamlit() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    # O contêiner com key ganha a classe .st-key-esconder_selo, usada no CSS acima.
    try:
        conteiner = st.container(key="esconder_selo")
    except TypeError:  # Streamlit antigo, sem key em st.container
        conteiner = st.container()
    with conteiner:
        if hasattr(st, "iframe"):
            st.iframe(_SCRIPT, height=1)
        else:  # versões do Streamlit sem st.iframe
            import streamlit.components.v1 as components
            components.html(_SCRIPT, height=1)
