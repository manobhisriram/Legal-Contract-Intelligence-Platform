"""
frontend/app.py — Streamlit client for the FastAPI backend.
The backend must be reachable at BACKEND_URL (default: http://localhost:8000).
"""
import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Legal Intelligence Agent",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.risk-badge-critical { background:#dc3545;color:white;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:700; }
.risk-badge-high { background:#fd7e14;color:white;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:700; }
.risk-badge-medium { background:#ffc107;color:#212529;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:700; }
.risk-badge-low { background:#28a745;color:white;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:700; }
</style>
""", unsafe_allow_html=True)


def api_get(path: str):
    try:
        r = requests.get(f"{BACKEND_URL}{path}", timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Ensure the FastAPI server is running.")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(path: str, data: dict = None, files: dict = None):
    try:
        if files:
            r = requests.post(f"{BACKEND_URL}{path}", files=files, data=data, timeout=120)
        else:
            r = requests.post(f"{BACKEND_URL}{path}", json=data, timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Ensure the FastAPI server is running.")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚖️ Legal Intelligence")
    st.caption(f"Backend: `{BACKEND_URL}`")

    # Health check
    health = api_get("/health")
    if health:
        st.success("✓ Backend connected")
    else:
        st.error("✗ Backend offline")
        st.caption("Run: `uvicorn backend.api.main:app --reload`")

    st.divider()
    page = st.radio("Navigate", [
        "🏠 Dashboard",
        "📤 Upload Contract",
        "📋 Review Contract",
        "🔍 Search",
        "📡 Regulatory Monitor",
        "🧪 Evaluation",
        "🔴 Red-Teaming",
    ], label_visibility="hidden")


# ─── Dashboard ────────────────────────────────────────────────────────────────

if page == "🏠 Dashboard":
    st.title("⚖️ Legal Intelligence Agent")
    st.caption("Autonomous multi-agent contract analysis · Milvus · Claude + GPT-4o + Gemini · MCP")

    stats = api_get("/api/dashboard/stats")
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Contracts Indexed", stats.get("total_contracts", 0))
        with col2:
            st.metric("Reviews Completed", stats.get("total_reviews", 0))
        with col3:
            st.metric("Regulatory Alerts", stats.get("regulatory_changes", 0))
        with col4:
            st.metric("Total AI Cost", f"${stats.get('total_cost_usd', 0):.4f}")

        if stats.get("risk_distribution"):
            st.divider()
            st.subheader("Risk Distribution")
            risk_dist = stats["risk_distribution"]
            cols = st.columns(len(risk_dist))
            for col, (level, count) in zip(cols, risk_dist.items()):
                with col:
                    st.metric(level.upper(), count)

    # Recent contracts
    st.divider()
    st.subheader("Recent Contracts")
    contracts = api_get("/api/contracts?limit=10")
    if contracts:
        for c in contracts:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(f"**{c['filename']}**")
            with col2:
                st.caption(c.get("contract_type", "general"))
            with col3:
                status_icon = "✅" if c["upload_status"] == "ready" else "⏳"
                st.caption(f"{status_icon} {c['upload_status']}")


# ─── Upload ────────────────────────────────────────────────────────────────────

elif page == "📤 Upload Contract":
    st.title("📤 Upload Contract")

    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_file = st.file_uploader("Select contract file", type=["pdf", "docx", "txt"])
    with col2:
        contract_type = st.selectbox("Type", ["general", "saas", "nda", "vendor", "employment"])
        enable_vision = st.checkbox("Vision processing", value=True)

    if uploaded_file and st.button("🚀 Upload & Process", type="primary"):
        with st.spinner(f"Processing {uploaded_file.name}..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {"contract_type": contract_type, "enable_vision": str(enable_vision).lower()}
            result = api_post("/api/contracts/upload", files=files, data=data)

        if result:
            st.success("✅ Uploaded successfully!")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Chunks", result["total_chunks"])
            with col_b:
                st.metric("Vision Pages", result["pages_with_vision"])
            with col_c:
                st.metric("Vision Used", "✓" if result["has_vision_processing"] else "✗")
            st.info(f"Contract ID: `{result['contract_id']}`")
            st.session_state["last_contract_id"] = result["contract_id"]
            st.session_state["last_contract_name"] = uploaded_file.name


# ─── Review ────────────────────────────────────────────────────────────────────

elif page == "📋 Review Contract":
    st.title("📋 Contract Review")

    contracts = api_get("/api/contracts?limit=50")
    if contracts:
        contract_options = {f"{c['filename']} ({c['id'][:8]}...)": c["id"] for c in contracts if c["upload_status"] == "ready"}
        if contract_options:
            selected_label = st.selectbox("Select contract", list(contract_options.keys()))
            selected_id = contract_options[selected_label]
            contract_type = st.selectbox("Contract type for template comparison", ["general", "saas", "nda", "vendor"])

            if st.button("🤖 Run 4-Agent Review", type="primary"):
                with st.spinner("Running 4-agent review (Extractor → Risk Analyst → Comparator → Synthesis)..."):
                    result = api_post("/api/contracts/review", {"contract_id": selected_id, "contract_type": contract_type})

                if result:
                    risk_color = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(result["overall_risk_level"], "⚪")
                    st.markdown(f"## {risk_color} {result['overall_risk_level'].upper()} RISK — Score: {result['overall_risk_score']}/100")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Clauses", result["total_clauses_found"])
                    with col2:
                        st.metric("High Risk", result["high_risk_count"])
                    with col3:
                        st.metric("Critical", result["critical_count"])
                    with col4:
                        st.metric("Confidence", f"{result['confidence_score']:.0f}%")

                    st.markdown("**Executive Summary**")
                    st.info(result["executive_summary"])

                    if result.get("deal_breakers"):
                        st.error("**⛔ Deal Breakers**")
                        for db in result["deal_breakers"]:
                            st.markdown(f"- {db}")

                    st.subheader("Top 5 Issues")
                    for issue in result.get("top_5_issues", []):
                        with st.expander(f"[{issue.get('severity','').upper()}] {issue.get('issue_title', 'Issue')}"):
                            st.markdown(issue.get("description", ""))
                            if issue.get("suggested_redline"):
                                st.markdown(f"**Suggested redline:** *{issue['suggested_redline']}*")
                            if issue.get("recommended_action"):
                                st.markdown(f"**Action:** `{issue['recommended_action']}`")

                    if result.get("negotiation_priorities"):
                        st.subheader("Negotiation Priorities")
                        for i, p in enumerate(result["negotiation_priorities"], 1):
                            st.markdown(f"{i}. {p}")

                    st.caption(f"Review time: {result['review_duration_seconds']:.1f}s | Cost: ${result['total_cost_usd']:.4f} | Models: {', '.join(result['models_used'])}")
        else:
            st.warning("No contracts ready for review. Upload a contract first.")
    else:
        st.warning("No contracts found. Upload a contract first.")


# ─── Search ────────────────────────────────────────────────────────────────────

elif page == "🔍 Search":
    st.title("🔍 Contract Library Search")

    query = st.text_input("Search your contract library", placeholder="Which contracts allow vendor AI training on our data?")
    top_k = st.slider("Results", 3, 20, 5)

    if query and st.button("🔍 Search", type="primary"):
        with st.spinner("Embedding → Searching Milvus → Reranking..."):
            result = api_post("/api/contracts/search", {"query": query, "top_k": top_k})

        if result:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"**Original:** {result['query'][:60]}")
            with col2:
                st.success(f"**Rewritten:** {result['rewritten_query'][:60]}")
            with col3:
                cache_str = "✅ Cache HIT" if result["cache_hit"] else "❌ Cache miss"
                st.warning(f"{cache_str} | Cost: ${result['total_cost_usd']:.4f}")

            st.divider()
            for i, r in enumerate(result.get("results", []), 1):
                with st.expander(f"Result {i} — Contract `{r.get('contract_id','')[:8]}...` Page {r.get('page_number','?')} (Relevance: {r.get('relevance_score',0):.2f})"):
                    if r.get("has_vision_enrichment"):
                        st.caption("👁️ Vision-enriched chunk")
                    st.markdown(r.get("text", "")[:600])


# ─── Regulatory ────────────────────────────────────────────────────────────────

elif page == "📡 Regulatory Monitor":
    st.title("📡 Regulatory Monitoring")

    if st.button("🔄 Trigger Check Now", type="primary"):
        with st.spinner("Checking all configured regulatory sources..."):
            result = api_post("/api/regulatory/check", {})
        if result:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Sources Checked", result["sources_checked"])
            with col2:
                st.metric("Changes Detected", result["changes_detected"])
            with col3:
                st.metric("Contracts Impacted", result["contracts_impacted"])

    st.divider()
    st.subheader("Recent Regulatory Changes")
    changes = api_get("/api/regulatory/changes?limit=20")
    if changes:
        for c in changes:
            icon = "🚨" if c.get("has_changes") else "✅"
            with st.expander(f"{icon} **{c['source_name']}** — {c['created_at'][:10]}"):
                st.markdown(c.get("change_summary") or "No change summary available.")
                st.caption(f"Source: {c['source_url'][:80]}")
    else:
        st.info("No regulatory changes recorded yet. Configure REGULATORY_SOURCES in .env and trigger a check.")


# ─── Evaluation ────────────────────────────────────────────────────────────────

elif page == "🧪 Evaluation":
    st.title("🧪 LLM Judge Evaluation")
    st.markdown("Custom 4-dimension judge built from scratch — Correctness · Severity Calibration · Completeness · Actionability")

    if st.button("▶️ Run Evaluation", type="primary"):
        with st.spinner("Running custom LLM judge on reviewed contracts..."):
            result = api_post("/api/evaluation/run", {"use_benchmark": True})

        if result:
            st.metric("Overall Score", f"{result['overall_score']*100:.1f}%")
            col1, col2, col3, col4 = st.columns(4)
            dims = result.get("dimension_scores", {})
            with col1:
                st.metric("Correctness", f"{dims.get('correctness',0)*100:.1f}%")
            with col2:
                st.metric("Severity Cal.", f"{dims.get('severity_calibration',0)*100:.1f}%")
            with col3:
                st.metric("Completeness", f"{dims.get('completeness',0)*100:.1f}%")
            with col4:
                st.metric("Actionability", f"{dims.get('actionability',0)*100:.1f}%")

    st.divider()
    st.subheader("Evaluation History")
    history = api_get("/api/evaluation/history")
    if history:
        import pandas as pd
        df = pd.DataFrame(history)
        df["overall_score"] = (df["overall_score"] * 100).round(1).astype(str) + "%"
        st.dataframe(df[["run_name", "total_contracts", "overall_score", "created_at"]], use_container_width=True, hide_index=True)


# ─── Red-Teaming ───────────────────────────────────────────────────────────────

elif page == "🔴 Red-Teaming":
    st.title("🔴 Red-Teaming Suite")
    st.markdown("50 adversarial contracts across 5 attack categories. Iterative patching with before/after failure rates.")

    iteration = st.number_input("Iteration number", min_value=1, max_value=10, value=1)

    if st.button("▶️ Run Red Team Evaluation", type="primary"):
        with st.spinner(f"Running {50} adversarial contracts through review agent..."):
            result = api_post("/api/redteam/run", {"iteration": iteration})

        if result:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Contracts", result["total_adversarial_contracts"])
            with col2:
                st.metric("Failure Rate", f"{result['failure_rate']*100:.1f}%")
            with col3:
                st.metric("Success Rate", f"{result['success_rate']*100:.1f}%")

            if result.get("category_breakdown"):
                st.subheader("By Attack Category")
                for cat, data in result["category_breakdown"].items():
                    st.metric(cat, f"{data['failure_rate']*100:.1f}% failure", f"{data['failed']}/{data['total']}")

            if result.get("patch_recommendations"):
                st.subheader("Recommended Patches")
                for patch in result["patch_recommendations"]:
                    with st.expander(f"🔧 {patch['category']}"):
                        st.markdown(patch["description"])
                        st.code(patch["prompt_addition"], language=None)
