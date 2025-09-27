from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def create_sample_pdf(file_name="sample_rental_agreement.pdf"):
    c = canvas.Canvas(file_name, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Sample Rental Agreement")
    y -= 40

    c.setFont("Helvetica", 12)
    content = [
        "This Rental Agreement is executed between Mr. John Doe (Landlord) and Ms. Jane Smith (Tenant).",
        "Property Address: 123 Main Street, Pune, India",
        "Rent: ₹15,000 per month",
        "Security Deposit: ₹30,000",
        "Notice Period: 1 month",
        "The landlord may evict the tenant anytime without prior notice.",
        "Deposit is non-refundable in case of violation of agreement.",
        "Rent can increase without notice during the lease period."
    ]

    for line in content:
        c.drawString(50, y, line)
        y -= 20

    c.save()
    print(f"Sample PDF created: {file_name}")

if __name__ == "__main__":
    create_sample_pdf()
