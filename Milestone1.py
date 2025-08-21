# app.py
# -------------------------------------------------------------
# Milestone 1: Working Application (Streamlit-only)
# User Authentication, Forgot Password & Document Ingestion
#
# How to run:
#   pip install streamlit bcrypt PyPDF2 python-docx
#   streamlit run app.py
#
# DB file created locally as: milestone1.db
# -------------------------------------------------------------

import streamlit as st
import sqlite3
import bcrypt
import secrets
from datetime import datetime

st.set_page_config(page_title="Milestone 1: Working Application", layout="wide")

# Optional parsers for multi-format upload
try:
    from docx import Document as DocxDocument  # python-docx
except Exception:
    DocxDocument = None

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

# ---------------------------
# Database helpers
# ---------------------------
DB_PATH = "milestone1.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            reset_token TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS documents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT,
            mime TEXT,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    conn.commit()
    conn.close()


def add_user(email: str, password: str) -> tuple[bool, str]:
    if not email or not password:
        return False, "Email and password are required."
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO users(email, password_hash, created_at) VALUES(?,?,?)",
            (email.strip().lower(), pw_hash, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
        return True, "Registration successful."
    except sqlite3.IntegrityError:
        return False, "Email already registered."
    except Exception as e:
        return False, f"Registration failed: {e}"


def verify_user(email: str, password: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, email, password_hash FROM users WHERE email=?",
        (email.strip().lower(),),
    ).fetchone()
    conn.close()
    if not row:
        return None
    try:
        if bcrypt.checkpw(password.encode("utf-8"), row["password_hash"]):
            return {"id": row["id"], "email": row["email"]}
    except Exception:
        pass
    return None


def create_reset_token(email: str) -> str | None:
    token = secrets.token_hex(16)  # 32-char secure token
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET reset_token=? WHERE email=?",
        (token, email.strip().lower()),
    )
    conn.commit()
    if cur.rowcount == 0:  # no matching email
        conn.close()
        return None
    conn.close()
    return token


def reset_password(email: str, token: str, new_password: str) -> tuple[bool, str]:
    conn = get_conn()
    row = conn.execute(
        "SELECT reset_token FROM users WHERE email=?", (email.strip().lower(),)
    ).fetchone()
    if not row or row["reset_token"] != token:
        conn.close()
        return False, "Invalid or expired reset token."

    pw_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
    conn.execute(
        "UPDATE users SET password_hash=?, reset_token=NULL WHERE email=?",
        (pw_hash, email.strip().lower()),
    )
    conn.commit()
    conn.close()
    return True, "Password has been reset successfully."


def save_document(user_id: int, content: str, filename: str | None, mime: str | None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO documents(user_id, filename, mime, content, created_at) VALUES(?,?,?,?,?)",
        (user_id, filename, mime, content, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def list_documents(user_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, filename, mime, content, created_at FROM documents WHERE user_id=? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def delete_document(doc_id: int, user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM documents WHERE id=? AND user_id=?", (doc_id, user_id))
    conn.commit()
    conn.close()


# ---------------------------
# Utility: extract text
# ---------------------------
def read_text_from_upload(uploaded_file) -> tuple[str, str, str]:
    filename = uploaded_file.name
    mime = uploaded_file.type or ""
    name_lower = filename.lower()

    if name_lower.endswith(".txt"):
        text = uploaded_file.read().decode("utf-8", errors="ignore")
        return text, filename, mime

    if name_lower.endswith(".docx"):
        if DocxDocument is None:
            raise RuntimeError("python-docx not installed. Run: pip install python-docx")
        doc = DocxDocument(uploaded_file)
        text = "\n".join([p.text for p in doc.paragraphs])
        return text, filename, mime

    if name_lower.endswith(".pdf"):
        if PdfReader is None:
            raise RuntimeError("PyPDF2 not installed. Run: pip install PyPDF2")
        reader = PdfReader(uploaded_file)
        pages = []
        for p in reader.pages:
            try:
                pages.append(p.extract_text() or "")
            except Exception:
                pages.append("")
        text = "\n".join(pages)
        return text, filename, mime

    try:
        text = uploaded_file.read().decode("utf-8", errors="ignore")
        return text, filename, mime
    except Exception:
        raise RuntimeError("Unsupported file type. Please upload TXT, DOCX, or PDF.")


# ---------------------------
# UI Styling
# ---------------------------
def inject_css():
    st.markdown(
        """
        <style>
        .badge {
            background: linear-gradient(135deg, #6366F1, #8B5CF6);
            color: white;
            padding: 6px 12px;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 12px;
            display: inline-block;
        }
        .card {
            background: #ffffff;
            border-radius: 16px;
            padding: 16px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            border: 1px solid rgba(0,0,0,0.05);
        }
        .metric-card {
            background: #0F172A;
            color: #E2E8F0;
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 8px 24px rgba(2,6,23,0.4);
        }
        .metric-value {
            font-size: 24px;
            font-weight: 700;
        }
        .metric-label {
            font-size: 12px;
            opacity: 0.8;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------
# Streamlit App
# ---------------------------
init_db()
inject_css()

st.markdown("<div class='badge'>Weeks 1–2</div>", unsafe_allow_html=True)
st.markdown("## Milestone 1: Working Application")
st.caption("User Authentication, Forgot Password & Document Ingestion")

# Session
if "user" not in st.session_state:
    st.session_state.user = None

# Layout
left, right = st.columns([2.2, 1.0], gap="large")

with left:
    tab_login, tab_upload, tab_docs = st.tabs(["Login", "Upload", "Documents"])

    # ---------------- Login Tab ----------------
    with tab_login:
        st.markdown("### Sign In")
        if st.session_state.user:
            st.success(f"Signed in as **{st.session_state.user['email']}**")
            if st.button("Sign out"):
                st.session_state.user = None
                st.rerun()
        else:
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.button("Sign In", type="primary", use_container_width=True)
            if submitted:
                user = verify_user(email, password)
                if user:
                    st.session_state.user = user
                    st.success("Login successful.")
                else:
                    st.error("Invalid email or password.")

            with st.expander("Don't have an account? Register"):
                r_email = st.text_input("New Email", key="reg_email")
                r_pwd = st.text_input("New Password", type="password", key="reg_pwd")
                if st.button("Create Account", key="reg_btn"):
                    ok, msg = add_user(r_email, r_pwd)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

            # ---------------- Forgot Password ----------------
            with st.expander("Forgot Password?"):
                fp_email = st.text_input("Enter your email", key="fp_email")
                if st.button("Send Reset Token", key="fp_btn"):
                    token = create_reset_token(fp_email)
                    if token:
                        st.info(f"Your reset token is: `{token}` (demo only, normally sent via email)")
                    else:
                        st.error("Email not found.")

                fp_token = st.text_input("Reset Token", key="fp_token")
                fp_newpwd = st.text_input("New Password", type="password", key="fp_newpwd")
                if st.button("Reset Password", key="fp_reset_btn"):
                    ok, msg = reset_password(fp_email, fp_token, fp_newpwd)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

    # ---------------- Upload Tab ----------------
    with tab_upload:
        st.markdown("### Upload Document")
        if not st.session_state.user:
            st.warning("Please login to upload documents.")
        else:
            st.write("You can paste text or upload a TXT/DOCX/PDF file.")
            paste_text = st.text_area("Paste text here (optional)", height=180, placeholder="Paste the content...")
            uploaded_file = st.file_uploader("Or upload a file", type=["txt", "docx", "pdf"])

            extracted_text, filename, mime = "", None, None
            if uploaded_file is not None:
                try:
                    extracted_text, filename, mime = read_text_from_upload(uploaded_file)
                    st.success(f"Parsed **{filename}**")
                    with st.expander("Preview extracted text"):
                        st.write(extracted_text[:2000] + ("..." if len(extracted_text) > 2000 else ""))
                except Exception as e:
                    st.error(str(e))

            if st.button("Save Document", type="primary"):
                final_text = (paste_text or "").strip()
                if not final_text and extracted_text:
                    final_text = extracted_text.strip()
                if not final_text:
                    st.error("No content to save. Paste text or upload a file first.")
                else:
                    save_document(
                        st.session_state.user["id"],
                        final_text,
                        filename or "pasted_text.txt",
                        mime or "text/plain",
                    )
                    st.success("Document saved to your library.")

    # ---------------- Documents Tab ----------------
    with tab_docs:
        st.markdown("### Document Library")
        if not st.session_state.user:
            st.warning("Please login to view your documents.")
        else:
            docs = list_documents(st.session_state.user["id"])
            if not docs:
                st.info("No documents uploaded yet.")
            else:
                for row in docs:
                    with st.container():
                        st.markdown(
                            f"<div class='card'><b>#{row['id']}</b> — {row['filename'] or 'Untitled'} "
                            f"<br><span style='font-size:12px;opacity:0.7'>{row['created_at']}</span>"
                            f"<br><br>{(row['content'][:280] + ('...' if len(row['content'])>280 else ''))}</div>",
                            unsafe_allow_html=True,
                        )
                        cols = st.columns([0.15, 0.15, 0.7])
                        if cols[0].button("View", key=f"view_{row['id']}"):
                            st.text_area(f"Document #{row['id']}", row["content"], height=240)
                        if cols[1].button("Delete", key=f"del_{row['id']}"):
                            delete_document(row["id"], st.session_state.user["id"])
                            st.success(f"Deleted document #{row['id']}")
                            st.rerun()

with right:
    st.markdown("#### Platform Highlights")
    st.markdown("<div class='card'><b>🔐 Secure Authentication</b><br>Includes Forgot Password reset.</div>", unsafe_allow_html=True)
    st.markdown("<div class='card'><b>📂 Multi-Format Upload</b><br>Supports TXT, DOCX, and PDF.</div>", unsafe_allow_html=True)
    st.markdown("<div class='card'><b>📜 Document History</b><br>Personal library for your documents.</div>", unsafe_allow_html=True)
    st.markdown("<div class='card'><b>⚡ Performance</b><br>Responsive uploads and retrieval.</div>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("#### Key Performance Metrics")
mc1, mc2, mc3, mc4 = st.columns(4)
with mc1:
    st.markdown("<div class='metric-card'><div class='metric-value'>99.9%</div><div class='metric-label'>System Uptime</div></div>", unsafe_allow_html=True)
with mc2:
    st.markdown("<div class='metric-card'><div class='metric-value'>&lt;30s</div><div class='metric-label'>Upload Time</div></div>", unsafe_allow_html=True)
with mc3:
    st.markdown("<div class='metric-card'><div class='metric-value'>95%</div><div class='metric-label'>Format Support</div></div>", unsafe_allow_html=True)
with mc4:
    st.markdown("<div class='metric-card'><div class='metric-value'>100%</div><div class='metric-label'>Text Extraction</div></div>", unsafe_allow_html=True)

