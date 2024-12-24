// Function to handle cart payments
function pay() {
    const paymentMethod = document.querySelector('input[name="paymentMethod"]:checked');
    if (!paymentMethod) {
        alert('Vui lòng chọn phương thức thanh toán!');
        return;
    }

    let deliveryAddress = null;
    if (paymentMethod.value === 'ONLINE') {
        deliveryAddress = document.getElementById('deliveryAddress').value;
        if (!deliveryAddress) {
            alert('Vui lòng nhập địa chỉ giao hàng!');
            return;
        }
    }

    const confirmMessage = paymentMethod.value === 'STORE_PICKUP'
        ? 'Xác nhận đặt hàng? Bạn sẽ cần đến lấy sách trong vòng 48 giờ.'
        : 'Xác nhận đặt hàng? Đơn hàng sẽ được giao đến địa chỉ của bạn.';

    if (confirm(confirmMessage)) {
        fetch('/api/pay', {
            method: 'POST',
            body: JSON.stringify({
                paymentMethod: paymentMethod.value,
                deliveryAddress: deliveryAddress
            }),
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 200) {
                alert(data.msg);
                location.reload();
            } else {
                alert(data.msg);
            }
        })
        .catch(err => {
            console.error('Error during payment:', err);
            alert('Đã xảy ra lỗi trong quá trình thanh toán!');
        });
    }
}

// Keep other existing functions unchanged
function addToCart(id, name, price, image) {
    fetch('/api/carts', {
        method: "POST",
        body: JSON.stringify({
            "id": id,
            "name": name,
            "price": price,
            "image": image
        }),
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(res => res.json()).then(data => {
        let counters = document.getElementsByClassName("cart-counter");
        for (let c of counters)
            c.innerHTML = data.total_quantity;
    })
}
// Function to update cart item quantity
function updateCart(id, obj) {
    fetch(`/api/carts/${id}`, {
        method: 'PUT',
        body: JSON.stringify({
            'quantity': obj.value
        }),
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(res => res.json()).then(data => {
        updateCartInfo(data);

        // Update line item subtotal
        const price = parseFloat(obj.getAttribute('data-price'));
        const quantity = parseInt(obj.value);
        const subtotal = price * quantity;

        const subtotalElement = document.getElementById(`subtotal-${id}`);
        if (subtotalElement) {
            subtotalElement.textContent = subtotal.toLocaleString('vi-VN') + ' ₫';
        }
    }).catch(err => console.error(err));
}

// Function to delete cart item
function deleteCart(id) {
    if (confirm('Bạn chắc chắn muốn xóa sản phẩm này?')) {
        fetch(`/api/carts/${id}`, {
            method: 'DELETE'
        }).then(res => res.json()).then(data => {
            updateCartInfo(data);
            // Remove the item from DOM
            let cart = document.getElementById(`cart${id}`);
            cart.remove();
        }).catch(err => console.error(err));
    }
}

function updateCartInfo(data) {
    // Update cart counter and total amount
    let counter = document.getElementsByClassName('cart-counter');
    let amount = document.getElementsByClassName('cart-amount');

    for (let i = 0; i < counter.length; i++)
        counter[i].innerText = data.total_quantity;

    for (let i = 0; i < amount.length; i++)
        amount[i].innerText = data.total_amount.toLocaleString('vi-VN') + ' ₫';
}
function addComment(productId) {
    const commentContent = document.getElementById("comment").value;
    if (!commentContent.trim()) {
        alert("Please enter a comment");
        return;
    }

    fetch(`/api/products/${productId}/comments`, {
        method: "POST",
        body: JSON.stringify({
            "content": commentContent
        }),
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 200 && data.comment) {
            // Create new comment element
            const commentHTML = `
                <div class="row mt-4 rounded comment-item" style="background: #f1f1f1; padding: 2rem;">
                    <div class="col-md-1">
                        <img src="${data.comment.user.avatar}" class="img-fluid" 
                             style="width:80px; height:80px; border-radius: 50%;"/>
                    </div>
                    <div class="col-md-11">
                        <p style="font-size: 1.4rem; font-weight: 700;">${data.comment.user.name}</p>
                        <p>${data.comment.content}</p>
                        <small class="text-muted">${moment(data.comment.created_date).fromNow()}</small>
                    </div>
                </div>
            `;

            // Find the comments container
            const commentsContainer = document.getElementById("comments-container");

            // Check if there's a "no comments" message and remove it
            const noCommentsMessage = commentsContainer.querySelector(".text-muted");
            if (noCommentsMessage && noCommentsMessage.textContent.includes("No comments yet")) {
                noCommentsMessage.remove();
            }

            // Add new comment to the beginning of the comments list
            commentsContainer.insertAdjacentHTML('afterbegin', commentHTML);

            // Clear comment input
            document.getElementById("comment").value = '';

            // Add success message
            const successMessage = document.createElement('div');
            successMessage.className = 'alert alert-success mt-2';
            successMessage.textContent = 'Comment added successfully!';
            document.getElementById("comment").parentNode.appendChild(successMessage);

            // Fade out and remove the success message after 2 seconds
            setTimeout(() => {
                successMessage.style.transition = 'opacity 0.5s';
                successMessage.style.opacity = '0';
                setTimeout(() => successMessage.remove(), 500);
            }, 2000);
        } else {
            throw new Error(data.message || "Error adding comment");
        }
    })
    .catch(err => {
        console.error("Error adding comment:", err);
        alert("Error adding comment. Please try again.");
    });
}

//
// Existing product import functionality
function addProductEntry() {
    const template = document.getElementById('productEntryTemplate');
    const clone = template.content.cloneNode(true);

    const quantityInput = clone.querySelector('.quantity-input');
    const select = clone.querySelector('.product-select');

    quantityInput.addEventListener('input', updateTotalQuantity);
    select.addEventListener('change', function() {
        updateStockInfo(this);
    });

    document.getElementById('productsList').appendChild(clone);
    updateTotalQuantity();
}

function removeProductEntry(button) {
    button.closest('.product-entry').remove();
    updateTotalQuantity();
}

function updateStockInfo(select) {
    const productEntry = select.closest('.product-entry');
    const stockInfo = productEntry.querySelector('.stock-info');
    const quantityInput = productEntry.querySelector('.quantity-input');
    const selectedOption = select.options[select.selectedIndex];

    if (selectedOption && selectedOption.value) {
        const currentStock = parseInt(selectedOption.dataset.stock);
        const remainingCapacity = 300 - currentStock;

        stockInfo.textContent = `Current stock: ${currentStock} | Max additional: ${remainingCapacity}`;
        quantityInput.max = remainingCapacity;
        validateQuantity(quantityInput);
    } else {
        stockInfo.textContent = '';
        quantityInput.max = '';
    }
}

function validateQuantity(input) {
    const warning = input.nextElementSibling;
    const value = parseInt(input.value) || 0;
    const max = parseInt(input.max);

    if (value <= 0) {
        warning.textContent = 'Quantity must be greater than 0';
        return false;
    } else if (max && value > max) {
        warning.textContent = `Maximum allowed quantity is ${max}`;
        return false;
    } else {
        warning.textContent = '';
        return true;
    }
}

function updateTotalQuantity() {
    const inputs = document.querySelectorAll('.quantity-input');
    let total = 0;

    inputs.forEach(input => {
        const value = parseInt(input.value) || 0;
        total += value;
        validateQuantity(input);
    });

    const totalDisplay = document.getElementById('totalQuantity');
    const indicator = document.getElementById('minQuantityIndicator');

    totalDisplay.textContent = `Total: ${total}`;

    if (total >= 150) {
        indicator.classList.remove('text-danger');
        indicator.classList.add('text-success');
        indicator.innerHTML = `<i class="fas fa-check-circle"></i> Min: 150`;
    } else {
        indicator.classList.remove('text-success');
        indicator.classList.add('text-danger');
        indicator.innerHTML = `<i class="fas fa-exclamation-circle"></i> Min: 150`;
    }
}

// Form submission handlers
function handleImportSubmit(event) {
    event.preventDefault();

    const entries = document.querySelectorAll('.product-entry');
    const importData = [];
    let isValid = true;
    let totalQuantity = 0;

    entries.forEach(entry => {
        const select = entry.querySelector('.product-select');
        const input = entry.querySelector('.quantity-input');

        if (!select.value) {
            alert('Please select a product for all entries');
            isValid = false;
            return;
        }

        if (!validateQuantity(input)) {
            isValid = false;
            return;
        }

        const quantity = parseInt(input.value);
        totalQuantity += quantity;

        importData.push({
            product_id: parseInt(select.value),
            quantity: quantity
        });
    });

    if (!isValid) {
        alert('Please correct the quantity errors before submitting.');
        return;
    }

    if (totalQuantity < 150) {
        alert(`Total quantity must be at least 150. Current total: ${totalQuantity}`);
        return;
    }

    // Show loading state
    const submitButton = event.target.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.innerHTML;
    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Importing...';

    fetch('/api/import', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ products: importData })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 200) {
            alert('Import successful!');
            location.reload(); // Refresh the page to show updated quantities
        } else {
            alert(data.message || 'Import failed. Please check the requirements.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred during import. Please try again.');
    })
    .finally(() => {
        // Restore button state
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
    });
}
function handleNewProductSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    // Basic validations
    const quantity = parseInt(formData.get('quantity'));
    const price = parseFloat(formData.get('price').replace(/,/g, ''));

    // Validate required fields
    if (!formData.get('name') || !formData.get('author') || !formData.get('category_id')) {
        alert('Please fill in all required fields');
        return;
    }

    // Validate quantity
    if (isNaN(quantity) || quantity <= 0 || quantity > 300) {
        alert('Quantity must be between 1 and 300');
        return;
    }

    // Validate price
    if (isNaN(price) || price <= 0) {
        alert('Please enter a valid price greater than 0');
        return;
    }

    // Create the request payload
    const payload = {
        name: formData.get('name').trim(),
        author: formData.get('author').trim(),
        description: formData.get('description') ? formData.get('description').trim() : '',
        category_id: parseInt(formData.get('category_id')),
        price: price,
        active: form.querySelector('[name="active"]').checked,
        quantity: quantity,
        image: formData.get('image') || ''
    };

    // Show loading state
    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.innerHTML;
    submitButton.disabled = true;
    submitButton.innerHTML = 'Importing...';

    fetch('/api/import/new', {
        method: 'POST',
        body: JSON.stringify(payload),
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 200) {
            alert('New product imported successfully!');
            location.reload();
        } else {
            alert(data.message || 'Import failed. Please check the requirements.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred during import. Please try again.');
    })
    .finally(() => {
        // Restore button state
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize existing product import form
    const importForm = document.getElementById('importForm');
    if (importForm) {
        importForm.addEventListener('submit', handleImportSubmit);
    }

    // Add initial product entry
    addProductEntry();

    // Initialize new product import form
    const newProductForm = document.getElementById('newProductForm');
    if (newProductForm) {
        newProductForm.addEventListener('submit', handleNewProductSubmit);
    }
});