# Journal de tests manuels RAG (5–10 questions)

Corpus testé : PDF dans `Documents/` (ex. Archive 2 à 8), collection Chroma `technical_docs`, mode basique (`USE_RERANKING=false`, `RETRIEVE_K=5`), LLM **Ollama** `llama3.2` après augmentation du timeout (`OLLAMA_HTTP_TIMEOUT`, défaut 600 s).

## Protocole

1. Ingérer : `python -m src.ingestion --input-dir ./Documents --collection technical_docs --reset`
2. Variables utiles : `LLM_PROVIDER=ollama`, `OLLAMA_MODEL=llama3.2`, et si besoin `OLLAMA_HTTP_TIMEOUT=600` (ou plus).
3. **Une question** : `python -m src.retrieval --collection technical_docs --verbose -q "..."`
4. **Lot** (remplit `eval/manual_runs.jsonl`, ignoré par git) : `python scripts/run_manual_questions.py`
5. Recopier ici les éléments saillants (réponse, sources, scores) ou joindre la date du fichier JSONL.

**Similarité cosinus** : avec l’index Chroma en espace cosinus, `cosine_similarity ≈ 1 - distance`. Si les scores semblent incohérents, ré-ingérer avec `--reset`.

---

## Résultats

| # | Question | Réponse observée (résumé) | Sources / scores utiles | Verdict | Problème probable |
|---|----------|---------------------------|-------------------------|---------|-------------------|
| 1 | De quoi parle chaque document principal ? | Le modèle synthétise plusieurs thèmes : RAG pour tâches NLP knowledge-intensive ; ChatDOC / structure PDF pour améliorer le QA ; évaluation de la qualité du retrieval en RAG ; bribes liées au code de citations de fichiers. | Top : Archive 3 p.15, cos ≈ **0.68** ; Archive 4 p.1, cos ≈ **0.66** ; Archive 7 p.31, cos ≈ **0.66** ; Archive 8 & 2 p.23, cos ≈ **0.66** (deux chunks quasi identiques). | **Partiel** | **Bruit PDF** : extraits p.23 (Arch 8 / 2) = code avec espaces entre caractères ; **duplication** de chunk entre deux PDFs ; la question « chaque document » pousse le LLM à **structurer** au-delà des 5 seuls passages (risque de détail approximatif). |
| 2 | Qu’est-ce que la génération augmentée par recherche (RAG) et à quels types de tâches NLP est-elle associée dans les extraits ? | *À compléter après exécution* (`run_manual_questions.py` ou CLI `--verbose`). | — | En attente | — |
| 3 | Quel problème les documents relient-ils aux PDF et aux systèmes de question-réponse avec LLM ? | *À compléter* | — | En attente | — |
| 4 | Comment ChatDOC ou la reconnaissance de structure de PDF est-elle présentée par rapport au RAG ? | *À compléter* | — | En attente | — |
| 5 | Qu’est-ce que « évaluer la qualité de la recherche » dans un pipeline RAG selon les références bibliographiques citées ? | *À compléter* | — | En attente | — |
| 6 | Les extraits mentionnent-ils LangChain ou des API d’embedding ? Dans quel rôle ? | *À compléter* | — | En attente | — |
| 7 | Résume en trois phrases ce qu’un ingénieur doit retenir sur les limites du RAG classique sur PDF. | *À compléter* | — | En attente | — |
| 8 | Y a-t-il dans les passages indexés du code Python lié aux citations de fichiers ou aux annotations ? | *À compléter* | — | En attente | — |

*(Les lignes 2–8 correspondent aux questions dans [`eval/questions.txt`](questions.txt) ; exécute le script batch puis complète les cellules à partir du JSONL ou du JSON `--verbose`.)*

---

## Synthèse qualitative (à jour après le test #1 + à enrichir après le batch)

**Ce qui fonctionne bien**

- Pipeline bout en bout : ingestion → retrieval top-k cosinus → prompt → **Ollama** sans timeout après réglage `OLLAMA_HTTP_TIMEOUT`.
- Scores **distance / cosine_similarity** cohérents avec un classement plausible (références bib RAG en tête, puis abstract ChatDOC, puis biblio « retrieval quality »).
- `--verbose` permet d’**inspecter** les previews et de comprendre vite si un chunk est du bruit.

**Ce qui fonctionne mal ou partiellement**

- **Extraction PDF** : certains blocs ressortent comme du code **avec espaces** (OCR / mise en page) → mauvais contexte pour le LLM.
- **Doublons** : le même extrait peut apparaître sous deux fichiers (ex. Arch 2 et Arch 8) → contexte redondant.
- **Question large** (« chaque document ») : le modèle **organise** une réponse multi-doc alors que seuls **k** passages sont fournis → interprétation / généralisation à surveiller (faithfulness).

**Pistes de correction**

- Pré / post-traitement PDF (autre lib, nettoyage des lignes « c o d e » espacé).
- Filtrer par **seuil de similarité** ou augmenter `RETRIEVE_K` puis **rerank** (`USE_RERANKING=true`) pour pousser les chunks code en bas.
- Prompt plus strict du type « ne cite que ce qui figure explicitement dans le contexte » (déjà partiellement dans le système ; à renforcer si besoin).
- Questions ciblées par PDF ou par section pour limiter l’ambiguïté.
