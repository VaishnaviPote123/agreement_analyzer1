import re
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from word2number import w2n
from transformers import pipeline
import fitz  # PyMuPDF for PDF

# -------------------------------
# Load summarizer (CPU-friendly)
# -------------------------------
print("Device set to use CPU")
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6", device=-1)

# -------------------------------
# Global variables
# -------------------------------
pdf_text_global = ""
summary_global = ""
key_terms_global = {}
risks_global = []

# -------------------------------
# Extract text from PDF
# -------------------------------
def extract_text_from_pdf(filepath):
    pdf = fitz.open(filepath)
    text = ""
    for page in pdf:
        text += page.get_text()
    return text

# -------------------------------
# Clean PDF text
# -------------------------------
def clean_pdf_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'Page \d+ of \d+', '', text, flags=re.I)
    return text

# -------------------------------
# Split text into chunks
# -------------------------------
def chunk_text(text, max_words=400):
    words = text.split()
    for i in range(0, len(words), max_words):
        yield " ".join(words[i:i + max_words])

# -------------------------------
# Extract Key Terms
# -------------------------------
def extract_key_terms(text):
    key_info = {}
    clean_text = " ".join(text.split())

    # Rent
    rent_match = re.search(r"\brent\b[^0-9a-zA-Z₹$€]{0,5}(₹|\$|€)?\s*([\d,]+)", clean_text, re.I)
    if rent_match:
        currency = rent_match.group(1) or ""
        rent_value = rent_match.group(2).replace(",", "")
        key_info['Rent'] = f"{currency}{rent_value} per month"
    else:
        key_info['Rent'] = "Not found"

    # Deposit
    deposit_match = re.search(r"\b(security deposit|deposit)\b[^0-9a-zA-Z₹$€]{0,5}(₹|\$|€)?\s*([\d,]+)", clean_text, re.I)
    if deposit_match:
        currency = deposit_match.group(2) or ""
        deposit_value = deposit_match.group(3).replace(",", "")
        key_info['Deposit'] = f"{currency}{deposit_value}"
    else:
        key_info['Deposit'] = "Not found"

    # Notice Period
    notice_match = re.search(r"\bnotice period\b[^0-9a-zA-Z]{0,5}(\d+|\w+)\s*(day|month|week)s?", clean_text, re.I)
    if notice_match:
        num_part = notice_match.group(1)
        unit = notice_match.group(2)
        try:
            if num_part.isdigit():
                key_info['Notice Period'] = num_part + " " + unit
            else:
                key_info['Notice Period'] = str(w2n.word_to_num(num_part)) + " " + unit
        except:
            key_info['Notice Period'] = num_part + " " + unit
    else:
        key_info['Notice Period'] = "Not found"

    return key_info

# -------------------------------
# Analyze PDF agreement
# -------------------------------
def analyze_agreement(pdf_text):
    pdf_text = clean_pdf_text(pdf_text)
    summary_chunks = []

    for chunk in chunk_text(pdf_text, max_words=400):
        summary_chunks.append(summarizer(chunk, max_length=130, min_length=50, do_sample=False)[0]['summary_text'])

    summary = " ".join(summary_chunks)
    key_terms = extract_key_terms(pdf_text)

    # Risk detection
    risks = []
    if "maintenance" not in pdf_text.lower():
        risks.append("No maintenance clause found")
    if "termination" not in pdf_text.lower():
        risks.append("No termination clause found")
    if "renewal" not in pdf_text.lower():
        risks.append("No renewal clause found")
    if "rent increase" in pdf_text.lower() and "notice" not in pdf_text.lower():
        risks.append("Rent can increase without notice")
    if "deposit refund" in pdf_text.lower() and "non-refundable" in pdf_text.lower():
        risks.append("Deposit is non-refundable")

    return summary, key_terms, risks

# -------------------------------
# Insert message into chat
# -------------------------------
def insert_message(sender, message):
    chat_window.configure(state='normal')
    if sender == "You":
        chat_window.insert(tk.END, f"👤 {sender}: {message}\n", "user")
    else:
        chat_window.insert(tk.END, f"🤖 {sender}: {message}\n", "bot")
    chat_window.configure(state='disabled')
    chat_window.yview(tk.END)

# -------------------------------
# Process user message
# -------------------------------
def process_user_message():
    user_input = user_entry.get().strip()
    if not user_input:
        return
    insert_message("You", user_input)
    user_entry.delete(0, tk.END)

    def generate_response():
        response = ""
        text_lower = user_input.lower()

        if not pdf_text_global:
            response = "Please upload a rental agreement PDF first."
        elif "rent" in text_lower:
            response = f"Rent: {key_terms_global.get('Rent','Not found')}"
        elif "deposit" in text_lower:
            response = f"Deposit: {key_terms_global.get('Deposit','Not found')}"
        elif "notice" in text_lower:
            response = f"Notice Period: {key_terms_global.get('Notice Period','Not found')}"
        elif "risks" in text_lower:
            if risks_global:
                response = "⚠ Risks Detected:\n" + "\n".join(f"- {r}" for r in risks_global)
            else:
                response = "✅ No major risks detected."
        elif "summarize" in text_lower:
            response = summary_global
        else:
            response = "I can answer questions about Rent, Deposit, Notice Period, Risks, and provide Summary."

        insert_message("Bot", response)

    threading.Thread(target=generate_response, daemon=True).start()

# -------------------------------
# Upload PDF
# -------------------------------
def upload_file():
    global pdf_text_global, summary_global, key_terms_global, risks_global
    filepath = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
    if filepath:
        def process_pdf():
            global pdf_text_global, summary_global, key_terms_global, risks_global
            pdf_text_global = extract_text_from_pdf(filepath)
            summary_global, key_terms_global, risks_global = analyze_agreement(pdf_text_global)
            insert_message("Bot", "PDF uploaded and analyzed successfully. You can now ask questions like:\n- show rent\n- show deposit\n- show risks\n- summarize agreement")
        threading.Thread(target=process_pdf, daemon=True).start()

# -------------------------------
# Tkinter GUI
# -------------------------------
root = tk.Tk()
root.title("✨ LegalDocBot - Chat Interface")
root.geometry("900x650")
root.configure(bg="#f7f7f7")

# Top Frame for PDF Upload
top_frame = tk.Frame(root, bg="#f7f7f7")
top_frame.pack(fill=tk.X, pady=10)

upload_btn = tk.Button(top_frame, text="📂 Upload Rental Agreement (PDF)", font=("Helvetica", 14), bg="#4CAF50", fg="white", padx=10, pady=5, command=upload_file)
upload_btn.pack(padx=10, side=tk.LEFT)

# Chat Window Frame
chat_frame = tk.Frame(root)
chat_frame.pack(fill=tk.BOTH, expand=True, padx=10)

chat_window = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, font=("Helvetica", 12))
chat_window.pack(fill=tk.BOTH, expand=True)
chat_window.tag_config("bot", foreground="#1f3b6e")
chat_window.tag_config("user", foreground="#2a9d8f")
chat_window.configure(state='disabled')

# Bottom Frame for User Input
bottom_frame = tk.Frame(root)
bottom_frame.pack(fill=tk.X, padx=10, pady=5)

user_entry = tk.Entry(bottom_frame, font=("Helvetica", 12))
user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,10))
user_entry.bind("<Return>", lambda event: process_user_message())

send_btn = tk.Button(bottom_frame, text="Send", font=("Helvetica", 12), bg="#4CAF50", fg="white", padx=10, command=process_user_message)
send_btn.pack(side=tk.LEFT)

root.mainloop()
