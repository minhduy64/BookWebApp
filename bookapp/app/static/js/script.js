function updateCartUI(data) {
    let counters = document.getElementsByClassName("cart-counter");
    for (let c of counters)
        c.innerText = data.total_quantity;

    let amounts = document.getElementsByClassName("cart-amount");
    for (let c of amounts)
        c.innerText = data.total_amount.toLocaleString();
}
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

function deleteCart(productId) {
    if (confirm("Bạn chắc chắn xóa không?") === true) {
        fetch(`/api/carts/${productId}`, {
            method: "delete"
        }).then(res => res.json()).then(data => {
            updateCartUI(data);

            document.getElementById(`cart${productId}`).style.display = "none";
        });
    }
}

function updateCart(productId, obj) {
    fetch(`/api/carts/${productId}`, {
        method: "put",
        body: JSON.stringify({
            "quantity": obj.value
        }),
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(res => res.json()).then(data => {
        updateCartUI(data);
    })
}

function pay() {
    if (confirm("Bạn chắc chắn thanh toán ?") === true) {
        fetch('/api/pay', {
            method: "post",
            headers: {
                "Content-Type": "application/json"
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 200) {
                alert("Thanh toán thành công!");
                location.reload();
            } else {
                alert(data.msg);
            }
        })
        .catch(err => {
            alert("Đã xảy ra lỗi trong quá trình thanh toán!");
            console.error(err);
        });
    }
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

            // Update quantity warning if needed
            validateQuantity(quantityInput);
        } else {
            stockInfo.textContent = '';
            quantityInput.max = '';
        }
    }

document.addEventListener('DOMContentLoaded', function() {
        addProductEntry();

        document.getElementById('importForm').addEventListener('submit', function(e) {
            e.preventDefault();
            handleImportSubmit();
        });
    });

    // Add a new product entry
    function addProductEntry() {
        const template = document.getElementById('productEntryTemplate');
        const clone = template.content.cloneNode(true);

        // Add event listeners
        const quantityInput = clone.querySelector('.quantity-input');
        const select = clone.querySelector('.product-select');

        quantityInput.addEventListener('input', updateTotalQuantity);
        select.addEventListener('change', function() {
            updateStockInfo(this);
        });

        document.getElementById('productsList').appendChild(clone);
        updateTotalQuantity();
    }

    // Remove a product entry
    function removeProductEntry(button) {
        button.closest('.product-entry').remove();
        updateTotalQuantity();
    }

    // Update stock info when product is selected
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

            // Update quantity warning if needed
            validateQuantity(quantityInput);
        } else {
            stockInfo.textContent = '';
            quantityInput.max = '';
        }
    }

    // Validate individual quantity input
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

    // Update total quantity and validate minimum requirement
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

    // Handle form submission
    function handleImportSubmit() {
        // Validate all quantities first
        const entries = document.querySelectorAll('.product-entry');
        const importData = [];
        let isValid = true;

        entries.forEach(entry => {
            const select = entry.querySelector('.product-select');
            const input = entry.querySelector('.quantity-input');

            if (!validateQuantity(input)) {
                isValid = false;
                return;
            }

            if (select.value && input.value) {
                importData.push({
                    product_id: parseInt(select.value),
                    quantity: parseInt(input.value)
                });
            }
        });

        if (!isValid) {
            alert('Please correct the quantity errors before submitting.');
            return;
        }

        // Validate total quantity
        const totalQuantity = importData.reduce((sum, item) => sum + item.quantity, 0);
        if (totalQuantity < 150) {
            alert(`Total quantity must be at least 150. Current total: ${totalQuantity}`);
            return;
        }

        // Submit to server
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
                location.reload();
            } else {
                alert(data.message || 'Import failed. Please check the requirements.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred during import. Please try again.');
        });
    }