"""Interface Streamlit : client HTTP de l'API, sans accès direct à la base ni au RAG."""

from __future__ import annotations

import os

import httpx
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
ASK_TIMEOUT = float(os.environ.get("FRONTEND_ASK_TIMEOUT", "600"))

st.set_page_config(page_title="Analyse-de-docs", page_icon="📄")


def api_get(path: str, timeout: float = 10.0) -> httpx.Response:
    return httpx.get(f"{API_BASE_URL}{path}", timeout=timeout)


def api_post(path: str, payload: dict, timeout: float = 10.0) -> httpx.Response:
    return httpx.post(f"{API_BASE_URL}{path}", json=payload, timeout=timeout)


def show_error(response: httpx.Response) -> None:
    try:
        detail = response.json().get("detail", response.text)
    except Exception:
        detail = response.text
    st.error(f"Erreur {response.status_code} : {detail}")


with st.sidebar:
    st.subheader("API")
    st.caption(API_BASE_URL)
    if st.button("Vérifier /health"):
        try:
            response = api_get("/health")
            if response.status_code == 200:
                st.success(response.json())
            else:
                show_error(response)
        except httpx.HTTPError as exc:
            st.error(f"API injoignable : {exc}")

st.title("Analyse-de-docs")

onglet_question, onglet_jobs = st.tabs(["Poser une question", "Jobs"])

with onglet_question:
    st.caption("Appelle `POST /api/ask` : réponse synchrone, nécessite Ollama et un index Chroma.")
    question = st.text_area("Question", height=120, placeholder="Quel est le sujet du document ?")
    verbose = st.checkbox("Afficher les extraits utilisés")

    if st.button("Envoyer", type="primary", disabled=not question.strip()):
        with st.spinner("Interrogation du pipeline RAG..."):
            try:
                response = api_post(
                    "/api/ask",
                    {"question": question.strip(), "verbose": verbose},
                    timeout=ASK_TIMEOUT,
                )
            except httpx.HTTPError as exc:
                st.error(f"API injoignable : {exc}")
            else:
                if response.status_code == 200:
                    result = response.json()
                    st.markdown(result["answer"])
                    if result.get("sources"):
                        st.subheader("Sources")
                        st.dataframe(result["sources"], width="stretch")
                    if result.get("chunk_details"):
                        st.subheader("Extraits")
                        for chunk in result["chunk_details"]:
                            with st.expander(f"{chunk.get('file_stem')} — page {chunk.get('page')}"):
                                st.write(chunk.get("text_preview"))
                else:
                    show_error(response)

with onglet_jobs:
    st.caption("`POST /jobs` enregistre le travail ; c'est le worker qui l'exécute.")

    with st.form("creer_job"):
        job_type = st.selectbox("Type", ["ingest", "simulate", "fail"])
        collection = st.text_input("Collection", value="technical_docs")
        input_dir = st.text_input("Dossier source", value="./Documents")
        reset = st.checkbox("Réinitialiser la collection")
        if st.form_submit_button("Créer le job", type="primary"):
            try:
                response = api_post(
                    "/jobs",
                    {
                        "job_type": job_type,
                        "collection": collection,
                        "input_dir": input_dir,
                        "reset": reset,
                    },
                )
            except httpx.HTTPError as exc:
                st.error(f"API injoignable : {exc}")
            else:
                if response.status_code == 201:
                    st.session_state["job_id"] = response.json()["id"]
                    st.success(f"Job créé : {st.session_state['job_id']}")
                else:
                    show_error(response)

    st.divider()

    job_id = st.text_input("Identifiant du job", value=st.session_state.get("job_id", ""))
    if st.button("Actualiser l'état", disabled=not job_id.strip()):
        try:
            response = api_get(f"/jobs/{job_id.strip()}")
        except httpx.HTTPError as exc:
            st.error(f"API injoignable : {exc}")
        else:
            if response.status_code == 200:
                job = response.json()
                status = job["status"]
                if status == "COMPLETED":
                    st.success(status)
                elif status == "FAILED":
                    st.error(f"{status} — {job['error_message']}")
                else:
                    st.info(f"{status} (relancer l'actualisation dans quelques secondes)")
                st.json(job)
            else:
                show_error(response)
