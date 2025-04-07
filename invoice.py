# invoice.py
from paypal_client import paypal_api

def create_invoice_link(amount: float, description: str, invoice_id: str) -> str:
    # Build the NVP params
    params = {
        "PAYMENTREQUEST_0_PAYMENTACTION": "Sale",
        "PAYMENTREQUEST_0_AMT":           f"{amount:.2f}",
        "PAYMENTREQUEST_0_CURRENCYCODE":  "USD",
        "L_PAYMENTREQUEST_0_NAME0":       description,
        "L_PAYMENTREQUEST_0_AMT0":        f"{amount:.2f}",
        "L_PAYMENTREQUEST_0_QTY0":        "1",
        "INVNUM":                         invoice_id,
    }

    # Kick off the Express Checkout
    resp = paypal_api._call("SetExpressCheckout", **params)
    if resp.get("ACK", [""])[0] not in ("Success", "SuccessWithWarning"):
        raise RuntimeError(f"PayPal error: {resp.get('L_LONGMESSAGE0') or resp}")

    token = resp["TOKEN"][0]
    # Construct the URL your user clicks to pay
    return paypal_api.express_checkout_url(token)
