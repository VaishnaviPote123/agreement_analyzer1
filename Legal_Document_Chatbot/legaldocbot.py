import tkinter as tk
from tkinter import filedialog, scrolledtext
import fitz  # PyMuPDF for PDFs
from transformers import pipeline
import re
from PIL import Image
import pytesseract
from word2number import w2n
import threading

# -------------------------------
# Tesseract OCR Path (Windows)
# -------------------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\Vaishnavi\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# -------------------------------
# Load summarizer (only once)
# -------------------------------
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# -------------------------------
# Global variables
# -------------------------------
pdf_text_global = ""
key_terms_global = {}
risks_global = {}

# -------------------------------
# Text Extraction
# -------------------------------
def extract_text_from_pdf(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

def extract_text_from_image(img_path):
    img = Image.open(img_path)
    return pytesseract.image_to_string(img)

# -------------------------------
# Summarization
# -------------------------------
def summarize_text(text, max_chunk=1000):
    chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
    summary = ""
    for chunk in chunks:
        out = summarizer(chunk, max_length=100, min_length=30, do_sample=False)
        summary += out[0]['summary_text'] + " "
    return summary.strip()

# -------------------------------
# Improved Key Term Extraction (Fixed)
# -------------------------------
def extract_key_terms(text):
    key_terms = {}

    # Rent
    rent_patterns = [
        r"(?:monthly\s+)?rent\s*(?:amount|is|of|:)?\s*([#₹$]?\s?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)",
        r"rent\s*[:\-]?\s*([#₹$]?\s?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)"
    ]
    rent = None
    for pattern in rent_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            rent = match.group(1).replace(",", "").strip()
            break
    key_terms['Rent'] = rent or "Not found"

    # Deposit
    deposit_patterns = [
        r"(?:security\s+deposit|deposit)\s*(?:is|of|:)?\s*([#₹$]?\s?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)"
    ]
    deposit = None
    for pattern in deposit_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            deposit = match.group(1).replace(",", "").strip()
            break
    key_terms['Deposit'] = deposit or "Not found"

    # Notice Period
    notice_pattern = r"notice period\s*(?:is|of|:)?\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(day|month|week)s?"
    match = re.search(notice_pattern, text, re.I)
    if match:
        num = match.group(1)
        try:
            num = str(int(num))
        except:
            try:
                num = str(w2n.word_to_num(num))
            except:
                pass
        unit = match.group(2)
        key_terms['Notice Period'] = f"{num} {unit}"
    else:
        key_terms['Notice Period'] = "Not found"

    return key_terms

# -------------------------------
# Risk Analysis
# -------------------------------
def analyze_risks(text):
    risks = []
    if "maintenance" not in text.lower():
        risks.append("No maintenance clause found")
    if "termination" not in text.lower():
        risks.append("No termination clause found")
    if "renewal" not in text.lower():
        risks.append("No renewal clause found")
    if "rent increase" in text.lower() and "notice" not in text.lower():
        risks.append("Rent can increase without notice")
    if "deposit refund" in text.lower() and "non-refundable" in text.lower():
        risks.append("Deposit is non-refundable")
    return risks

# -------------------------------
# Threaded File Upload
# -------------------------------
def process_file(file_path):
    global pdf_text_global, key_terms_global, risks_global
    if file_path.lower().endswith(".pdf"):
        pdf_text_global = extract_text_from_pdf(file_path)
    else:
        pdf_text_global = extract_text_from_image(file_path)

    key_terms_global = extract_key_terms(pdf_text_global)
    risks_global = analyze_risks(pdf_text_global)

    insert_message("Bot", "✅ File analyzed successfully! Use buttons or type a query.")

def upload_file():
    file_path = filedialog.askopenfilename(filetypes=[("PDF/Image", "*.pdf *.png *.jpg *.jpeg")])
    if file_path:
        insert_message("Bot", "⏳ Analyzing file, please wait…")
        threading.Thread(target=process_file, args=(file_path,), daemon=True).start()

# -------------------------------
# Threaded Summary
# -------------------------------
def process_summary():
    summary = summarize_text(pdf_text_global)
    insert_message("Bot", f"📝 Agreement Summary:\n{summary}")

def show_summary():
    if not pdf_text_global:
        insert_message("Bot", "Please upload a rental agreement first.")
    else:
        insert_message("Bot", "⏳ Summarizing agreement, please wait…")
        threading.Thread(target=process_summary, daemon=True).start()

# -------------------------------
# Chatbot Logic
# -------------------------------
def handle_query():
    query = user_entry.get("1.0", tk.END).strip().lower()
    user_entry.delete("1.0", tk.END)
    if not query:
        return
    insert_message("You", query)
    if "rent" in query:
        show_rent()
    elif "deposit" in query:
        show_deposit()
    elif "notice" in query:
        show_notice()
    elif "risk" in query:
        show_risks()
    elif "summary" in query or "summarize" in query:
        show_summary()
    else:
        insert_message("Bot", "❓ I didn’t understand. Use buttons or ask about Rent, Deposit, Notice, Risks, Summary.")

# -------------------------------
# Insert message with colors
# -------------------------------
def insert_message(sender, message, color="black"):
    chat_window.config(state=tk.NORMAL)
    chat_window.insert(tk.END, f"{sender}: ", "bold")
    chat_window.insert(tk.END, f"{message}\n\n", color)
    chat_window.config(state=tk.DISABLED)
    chat_window.see(tk.END)

# -------------------------------
# Buttons
# -------------------------------
def show_rent():
    insert_message("Bot", f"💰 Rent: {key_terms_global.get('Rent','Not found')}")

def show_deposit():
    insert_message("Bot", f"🏦 Deposit: {key_terms_global.get('Deposit','Not found')}")

def show_notice():
    insert_message("Bot", f"📅 Notice Period: {key_terms_global.get('Notice Period','Not found')}")

def show_risks():
    if risks_global:
        risk_text = "\n".join(f"- {r}" for r in risks_global)
        insert_message("Bot", "⚠ Risks Detected:\n" + risk_text, color="red")
    else:
        insert_message("Bot", "✅ No major risks detected.", color="green")

# -------------------------------
# Tkinter GUI
# -------------------------------
root = tk.Tk()
root.title("📜 LegalDocBot")
root.geometry("700x600")
root.configure(bg="#f7f7f7")

# Chat window
chat_window = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Helvetica", 12), state=tk.DISABLED, bg="white")
chat_window.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Define text styles
chat_window.tag_configure("bold", font=("Helvetica", 12, "bold"))
chat_window.tag_configure("red", foreground="red")
chat_window.tag_configure("green", foreground="green")
chat_window.tag_configure("black", foreground="black")

# Quick Buttons
button_frame = tk.Frame(root, bg="#f7f7f7")
button_frame.pack(fill=tk.X, padx=10, pady=5)

tk.Button(button_frame, text="💰 Show Rent", bg="#2a9d8f", fg="white", command=show_rent).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="🏦 Show Deposit", bg="#264653", fg="white", command=show_deposit).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="📅 Notice Period", bg="#e9c46a", fg="black", command=show_notice).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="⚠ Show Risks", bg="#e76f51", fg="white", command=show_risks).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="📝 Summarize", bg="#457b9d", fg="white", command=show_summary).pack(side=tk.LEFT, padx=5)

# User input
user_entry = tk.Text(root, height=2, font=("Helvetica", 12))
user_entry.pack(padx=10, pady=5, fill=tk.X)

control_frame = tk.Frame(root, bg="#f7f7f7")
control_frame.pack(fill=tk.X, padx=10, pady=5)

tk.Button(control_frame, text="Send", bg="#2a9d8f", fg="white", command=handle_query).pack(side=tk.RIGHT, padx=5)
tk.Button(control_frame, text="📂 Upload File", bg="#264653", fg="white", command=upload_file).pack(side=tk.RIGHT, padx=5)

# Welcome message
insert_message("Bot", "👋 Hello! Upload a rental agreement PDF or PNG/JPG to get started.")

root.mainloop()
