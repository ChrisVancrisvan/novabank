from pdf_engine import generate_transfer_pdf


response = generate_transfer_pdf(

    user_id="USR-00001",

    amount=500,

    from_account="cuenta_debito",

    to_account="inversion_hey",

    new_source_balance=12000,

    new_target_balance=25000
)


print(response)