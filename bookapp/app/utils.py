import hashlib


def count_cart(cart):
    total_quantity, total_amount = 0, 0

    if cart:
        for c in cart.values():
            total_quantity += c['quantity']
            total_amount += c['quantity'] * c['price']
    return {
        "total_quantity": total_quantity,
        "total_amount": total_amount
    }


def check_password(password, hashed_password):
    hashed = str(hashlib.md5(password.encode('utf-8')).hexdigest())
    return hashed == hashed_password
