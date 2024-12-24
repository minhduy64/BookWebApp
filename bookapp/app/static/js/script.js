// Hàm xử lý thanh toán giỏ hàng
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
// Chức năng cập nhật số lượng sản phẩm trong giỏ hàng
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

        // Cập nhật tổng phụ của chi tiết đơn hàng
        const price = parseFloat(obj.getAttribute('data-price'));
        const quantity = parseInt(obj.value);
        const subtotal = price * quantity;

        const subtotalElement = document.getElementById(`subtotal-${id}`);
        if (subtotalElement) {
            subtotalElement.textContent = subtotal.toLocaleString('vi-VN') + ' ₫';
        }
    }).catch(err => console.error(err));
}

// Hàm xóa sản phẩm trong giỏ hàng
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
    // Cập nhật bộ đếm giỏ hàng và tổng số tiền
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
        alert("Vui lòng nhập bình luận");
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

            // Tìm comments container
            const commentsContainer = document.getElementById("comments-container");

            // Kiểm tra xem có thông báo "không có bình luận" không và xóa nó
            const noCommentsMessage = commentsContainer.querySelector(".text-muted");
            if (noCommentsMessage && noCommentsMessage.textContent.includes("Chưa có bình luận nào")) {
                noCommentsMessage.remove();
            }

            // Thêm chú thích mới vào đầu danh sách chú thích
            commentsContainer.insertAdjacentHTML('afterbegin', commentHTML);

            // Xóa comment input
            document.getElementById("comment").value = '';

            // Thêm thông báo thành công
            const successMessage = document.createElement('div');
            successMessage.className = 'alert alert-success mt-2';
            successMessage.textContent = 'Đã thêm bình luận thành công!';
            document.getElementById("comment").parentNode.appendChild(successMessage);

            // Làm mờ dần và xóa thông báo thành công sau 2 giây
            setTimeout(() => {
                successMessage.style.transition = 'opacity 0.5s';
                successMessage.style.opacity = '0';
                setTimeout(() => successMessage.remove(), 500);
            }, 2000);
        } else {
            throw new Error(data.message || "Lỗi khi thêm nhận xét");
        }
    })
    .catch(err => {
        console.error("Lỗi khi thêm nhận xét:", err);
        alert("Lỗi khi thêm nhận xét. Vui lòng thử lại.");
    });
}


// Chức năng nhập sản phẩm hiện có
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

        stockInfo.textContent = `Số lượng hiện tại ${currentStock} | Thêm tối đa: ${remainingCapacity}`;
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
        warning.textContent = 'Số lượng phải lớn hơn 0';
        return false;
    } else if (max && value > max) {
        warning.textContent = `Số lượng tối đa cho phép là ${max}`;
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

    totalDisplay.textContent = `Tổng cộng: ${total}`;

    if (total >= 150) {
        indicator.classList.remove('text-danger');
        indicator.classList.add('text-success');
        indicator.innerHTML = `<i class="fas fa-check-circle"></i>Tối thiểu: 150`;
    } else {
        indicator.classList.remove('text-success');
        indicator.classList.add('text-danger');
        indicator.innerHTML = `<i class="fas fa-exclamation-circle"></i>Tối thiểu: 150`;
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
            alert('Vui lòng chọn một sản phẩm cho tất cả các mục');
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
        alert('Vui lòng sửa số lượng trước khi gửi.');
        return;
    }

    if (totalQuantity < 150) {
        alert(`Tổng số lượng phải ít nhất là 150. Tổng số hiện tại: ${totalQuantity}`);
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
            alert('Nhập hàng thành công!');
            location.reload(); // Làm mới trang để hiển thị số lượng cập nhật
        } else {
            alert(data.message || 'Nhập hàng thất bại. Vui lòng kiểm tra các yêu cầu.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Đã xảy ra lỗi trong quá trình nhập. Vui lòng thử lại.');
    })
    .finally(() => {
        // Khôi phục trạng thái nút
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
    });
}
function handleNewProductSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    // Xác thực cơ bản
    const quantity = parseInt(formData.get('quantity'));
    const price = parseFloat(formData.get('price').replace(/,/g, ''));

    // Xác thực các trường bắt buộc
    if (!formData.get('name') || !formData.get('author') || !formData.get('category_id')) {
        alert('Vui lòng điền vào tất cả các trường bắt buộc');
        return;
    }

    // Xác thực số lượng
    if (isNaN(quantity) || quantity <= 0 || quantity > 300) {
        alert('Số lượng phải từ 1 đến 300');
        return;
    }

    // Xác thực giá
    if (isNaN(price) || price <= 0) {
        alert('Vui lòng nhập giá hợp lệ lớn hơn 0');
        return;
    }

    // Tạo request payload
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

    // Hiển thị trạng thái tải
    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.innerHTML;
    submitButton.disabled = true;
    submitButton.innerHTML = 'Đang nhập...';

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
            alert('Sản phẩm mới được nhập hàng thành công!');
            location.reload();
        } else {
            alert(data.message || 'Nhập hàng không thành công. Vui lòng kiểm tra các yêu cầu.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Đã xảy ra lỗi trong quá trình nhập. Vui lòng thử lại.');
    })
    .finally(() => {
        // Khôi phục button state
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo form import sản phẩm hiện có
    const importForm = document.getElementById('importForm');
    if (importForm) {
        importForm.addEventListener('submit', handleImportSubmit);
    }

    // Thêm mục nhập sản phẩm ban đầu
    addProductEntry();

    // Khởi tạo form import sản phẩm mới
    const newProductForm = document.getElementById('newProductForm');
    if (newProductForm) {
        newProductForm.addEventListener('submit', handleNewProductSubmit);
    }
});