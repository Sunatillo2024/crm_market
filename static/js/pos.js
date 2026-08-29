(() => {
    "use strict";

    const app = document.getElementById("posApp");

    if (!app) {
        return;
    }
    const successReceiptLink = document.getElementById("successReceiptLink");
    const productSearchUrl = app.dataset.productSearchUrl;
    const checkoutUrl = app.dataset.checkoutUrl;

    const csrfToken = document.querySelector(
        "[name=csrfmiddlewaretoken]"
    ).value;

    const searchInput = document.getElementById(
        "productSearchInput"
    );

    const searchStatus = document.getElementById(
        "productSearchStatus"
    );

    const productResults = document.getElementById(
        "productResults"
    );

    const cartCount = document.getElementById("cartCount");
    const emptyCart = document.getElementById("emptyCart");
    const cartItems = document.getElementById("cartItems");

    const cashPaymentFields = document.getElementById(
        "cashPaymentFields"
    );

    const amountReceivedInput = document.getElementById(
        "amountReceivedInput"
    );

    const exactCashButton = document.getElementById(
        "exactCashButton"
    );

    const paymentTotal = document.getElementById(
        "paymentTotal"
    );

    const changeLabel = document.getElementById(
        "changeLabel"
    );

    const changeAmount = document.getElementById(
        "changeAmount"
    );

    const checkoutButton = document.getElementById(
        "checkoutButton"
    );

    const checkoutError = document.getElementById(
        "checkoutError"
    );

    const notice = document.getElementById("posNotice");

    const successOverlay = document.getElementById(
        "saleSuccessOverlay"
    );

    const successSaleNumber = document.getElementById(
        "successSaleNumber"
    );

    const successTotal = document.getElementById(
        "successTotal"
    );

    const successReceived = document.getElementById(
        "successReceived"
    );

    const successChange = document.getElementById(
        "successChange"
    );

    const startNextSaleButton = document.getElementById(
        "startNextSaleButton"
    );

    const cart = new Map();
    const searchProducts = new Map();

    let searchTimer = null;
    let searchController = null;
    let noticeTimer = null;
    let isSubmitting = false;

    const moneyFormatter = new Intl.NumberFormat(
        "uz-UZ",
        {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }
    );

    function escapeHtml(value) {
        const element = document.createElement("div");

        element.textContent = value ?? "";

        return element.innerHTML;
    }

    function parseNumber(value) {
        const normalizedValue = String(
            value ?? ""
        )
            .trim()
            .replace(",", ".");

        const number = Number(normalizedValue);

        return Number.isFinite(number)
            ? number
            : NaN;
    }

    function roundMoney(value) {
        return Math.round(
            (value + Number.EPSILON) * 100
        ) / 100;
    }

    function roundQuantity(value) {
        return Math.round(
            (value + Number.EPSILON) * 1000
        ) / 1000;
    }

    function formatMoney(value) {
        return `${moneyFormatter.format(
            Number(value) || 0
        )} som`;
    }

    function formatQuantity(value, unit) {
        const number = Number(value) || 0;

        if (unit === "piece") {
            return String(
                Math.round(number)
            );
        }

        return number
            .toFixed(3)
            .replace(/\.?0+$/, "");
    }

    function selectedPaymentMethod() {
        const selectedInput = document.querySelector(
            'input[name="payment_method"]:checked'
        );

        return selectedInput
            ? selectedInput.value
            : "cash";
    }

    function showNotice(message, type = "danger") {
        window.clearTimeout(noticeTimer);

        notice.textContent = message;
        notice.className = (
            `pos-notice is-visible ${type}`
        );

        noticeTimer = window.setTimeout(
            () => {
                notice.className = "pos-notice";
            },
            3000
        );
    }

    function showCheckoutError(message) {
        checkoutError.textContent = message;
        checkoutError.hidden = false;
    }

    function clearCheckoutError() {
        checkoutError.textContent = "";
        checkoutError.hidden = true;
    }

    function normalizeProduct(rawProduct) {
        return {
            id: Number(rawProduct.id),
            name: rawProduct.name,
            barcode: rawProduct.barcode || "",
            price: parseNumber(
                rawProduct.sale_price
            ),
            stock: parseNumber(
                rawProduct.stock_quantity
            ),
            unit: rawProduct.unit,
            unitLabel: rawProduct.unit_label,
            isAvailable: rawProduct.is_available,
        };
    }

    function renderProductResults(products) {
        searchProducts.clear();

        if (!products.length) {
            productResults.innerHTML = `
                <div class="pos-no-products">
                    <i class="bi bi-search"></i>

                    <strong>
                        Mahsulot topilmadi
                    </strong>

                    <p>
                        Nom yoki barkodni tekshirib qayta qidiring.
                    </p>
                </div>
            `;

            return;
        }

        productResults.innerHTML = products
            .map((product) => {
                searchProducts.set(
                    String(product.id),
                    product
                );

                const stockText = (
                    `${formatQuantity(
                        product.stock,
                        product.unit
                    )} ${escapeHtml(product.unitLabel)}`
                );

                return `
                    <button
                        type="button"
                        class="pos-product-card ${
                            product.isAvailable
                                ? ""
                                : "is-unavailable"
                        }"
                        data-product-id="${product.id}"
                        ${product.isAvailable ? "" : "disabled"}
                    >
                        <span class="pos-product-card-icon">
                            <i class="bi bi-box-seam"></i>
                        </span>

                        <span class="pos-product-card-content">
                            <strong>
                                ${escapeHtml(product.name)}
                            </strong>

                            <small>
                                ${
                                    product.barcode
                                        ? escapeHtml(product.barcode)
                                        : "Barkodsiz"
                                }
                            </small>
                        </span>

                        <span class="pos-product-card-footer">
                            <b>
                                ${formatMoney(product.price)}
                            </b>

                            <small>
                                ${
                                    product.isAvailable
                                        ? stockText
                                        : "Tugagan"
                                }
                            </small>
                        </span>
                    </button>
                `;
            })
            .join("");
    }

    async function loadProducts({
        addExact = false,
    } = {}) {
        const query = searchInput.value.trim();

        if (searchController) {
            searchController.abort();
        }

        searchController = new AbortController();

        searchStatus.hidden = false;

        try {
            const response = await fetch(
                `${productSearchUrl}?q=${encodeURIComponent(query)}`,
                {
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    signal: searchController.signal,
                }
            );

            if (!response.ok) {
                throw new Error(
                    "Mahsulotlarni yuklab bo‘lmadi."
                );
            }

            const data = await response.json();

            const products = data.results.map(
                normalizeProduct
            );

            renderProductResults(products);

            if (addExact && query) {
                const exactProduct = products.find(
                    (product) => (
                        product.barcode === query
                    )
                );

                if (exactProduct) {
                    addProduct(exactProduct);
                    searchInput.select();

                    return;
                }

                if (products.length === 1) {
                    addProduct(products[0]);
                    searchInput.select();
                }
            }

        } catch (error) {
            if (error.name === "AbortError") {
                return;
            }

            productResults.innerHTML = `
                <div class="pos-no-products error">
                    <i class="bi bi-exclamation-triangle"></i>

                    <strong>
                        Yuklashda xatolik
                    </strong>

                    <p>
                        Sahifani yangilab qayta urinib ko‘ring.
                    </p>
                </div>
            `;

        } finally {
            searchStatus.hidden = true;
        }
    }

    function addProduct(product) {
        if (!product.isAvailable || product.stock <= 0) {
            showNotice(
                `${product.name} omborda qolmagan.`
            );

            return;
        }

        const existingItem = cart.get(
            product.id
        );

        const currentQuantity = existingItem
            ? existingItem.quantity
            : 0;

        const nextQuantity = roundQuantity(
            currentQuantity + 1
        );

        if (nextQuantity > product.stock) {
            showNotice(
                `${product.name}: omborda faqat ${
                    formatQuantity(
                        product.stock,
                        product.unit
                    )
                } ${product.unitLabel} mavjud.`
            );

            return;
        }

        cart.set(
            product.id,
            {
                product,
                quantity: nextQuantity,
            }
        );

        renderCart();

        showNotice(
            `${product.name} savatga qo‘shildi.`,
            "success"
        );
    }

    function calculateTotal() {
        let total = 0;

        cart.forEach((item) => {
            total += roundMoney(
                item.quantity
                * item.product.price
            );
        });

        return roundMoney(total);
    }

    function renderCart() {
        cartCount.textContent = (
            `${cart.size} xil`
        );

        if (!cart.size) {
            emptyCart.hidden = false;
            cartItems.hidden = true;
            cartItems.innerHTML = "";

            updatePayment();

            return;
        }

        emptyCart.hidden = true;
        cartItems.hidden = false;

        cartItems.innerHTML = Array.from(
            cart.values()
        )
            .map((item) => {
                const product = item.product;

                const step = (
                    product.unit === "piece"
                        ? 1
                        : 0.1
                );

                const lineTotal = roundMoney(
                    item.quantity * product.price
                );

                return `
                    <article
                        class="pos-cart-item"
                        data-product-id="${product.id}"
                    >
                        <div class="pos-cart-item-main">
                            <div>
                                <strong>
                                    ${escapeHtml(product.name)}
                                </strong>

                                <small>
                                    ${formatMoney(product.price)}
                                    / ${escapeHtml(product.unitLabel)}
                                </small>
                            </div>

                            <button
                                type="button"
                                class="pos-cart-remove"
                                data-action="remove"
                                data-product-id="${product.id}"
                                title="Savatdan olib tashlash"
                            >
                                <i class="bi bi-trash3"></i>
                            </button>
                        </div>

                        <div class="pos-cart-item-bottom">
                            <div class="pos-quantity-control">
                                <button
                                    type="button"
                                    data-action="decrease"
                                    data-product-id="${product.id}"
                                >
                                    <i class="bi bi-dash"></i>
                                </button>

                                <input
                                    type="number"
                                    data-action="quantity"
                                    data-product-id="${product.id}"
                                    min="${step}"
                                    max="${product.stock}"
                                    step="${
                                        product.unit === "piece"
                                            ? "1"
                                            : "0.001"
                                    }"
                                    value="${formatQuantity(
                                        item.quantity,
                                        product.unit
                                    )}"
                                >

                                <button
                                    type="button"
                                    data-action="increase"
                                    data-product-id="${product.id}"
                                >
                                    <i class="bi bi-plus"></i>
                                </button>
                            </div>

                            <strong class="pos-cart-line-total">
                                ${formatMoney(lineTotal)}
                            </strong>
                        </div>
                    </article>
                `;
            })
            .join("");

        updatePayment();
    }

    function updatePayment() {
        const total = calculateTotal();
        const paymentMethod = selectedPaymentMethod();

        paymentTotal.textContent = formatMoney(
            total
        );

        cashPaymentFields.hidden = (
            paymentMethod !== "cash"
        );

        let canCheckout = cart.size > 0;

        if (paymentMethod === "card") {
            changeLabel.textContent = "Qaytim";
            changeAmount.textContent = formatMoney(0);
            changeAmount.className = (
                "pos-change-amount positive"
            );

        } else {
            const received = parseNumber(
                amountReceivedInput.value
            );

            if (
                Number.isFinite(received)
                && received >= total
                && total > 0
            ) {
                const change = roundMoney(
                    received - total
                );

                changeLabel.textContent = "Qaytim";
                changeAmount.textContent = (
                    formatMoney(change)
                );

                changeAmount.className = (
                    "pos-change-amount positive"
                );

            } else {
                const safeReceived = Number.isFinite(
                    received
                )
                    ? received
                    : 0;

                const missingAmount = Math.max(
                    roundMoney(total - safeReceived),
                    0
                );

                changeLabel.textContent = "Yetishmayapti";
                changeAmount.textContent = (
                    formatMoney(missingAmount)
                );

                changeAmount.className = (
                    "pos-change-amount negative"
                );

                canCheckout = false;
            }
        }

        checkoutButton.disabled = (
            !canCheckout
            || isSubmitting
        );
    }

    function changeCartQuantity(
        productId,
        newQuantity
    ) {
        const item = cart.get(productId);

        if (!item) {
            return;
        }

        const product = item.product;

        if (
            !Number.isFinite(newQuantity)
            || newQuantity <= 0
        ) {
            showNotice(
                "Mahsulot miqdori 0 dan katta bo‘lishi kerak."
            );

            renderCart();

            return;
        }

        if (
            product.unit === "piece"
            && !Number.isInteger(newQuantity)
        ) {
            showNotice(
                "Dona mahsulot miqdori butun son bo‘lishi kerak."
            );

            renderCart();

            return;
        }

        newQuantity = roundQuantity(
            newQuantity
        );

        if (newQuantity > product.stock) {
            showNotice(
                `${product.name}: omborda faqat ${
                    formatQuantity(
                        product.stock,
                        product.unit
                    )
                } ${product.unitLabel} mavjud.`
            );

            renderCart();

            return;
        }

        item.quantity = newQuantity;

        cart.set(
            productId,
            item
        );

        renderCart();
    }

    function flattenErrors(errors) {
        if (!errors) {
            return "Savdoni yakunlab bo‘lmadi.";
        }

        return Object.values(errors)
            .flat()
            .join(" ");
    }

    async function submitCheckout() {
        clearCheckoutError();

        if (!cart.size || isSubmitting) {
            return;
        }

        const paymentMethod = selectedPaymentMethod();
        const total = calculateTotal();

        let amountReceived = total.toFixed(2);

        if (paymentMethod === "cash") {
            const received = parseNumber(
                amountReceivedInput.value
            );

            if (
                !Number.isFinite(received)
                || received < total
            ) {
                showCheckoutError(
                    "Mijoz bergan pul yetarli emas."
                );

                return;
            }

            amountReceived = received.toFixed(2);
        }

        const items = Array.from(
            cart.values()
        ).map((item) => ({
            product_id: item.product.id,
            quantity: (
                item.product.unit === "piece"
                    ? String(
                        Math.round(item.quantity)
                    )
                    : item.quantity.toFixed(3)
            ),
        }));

        isSubmitting = true;

        checkoutButton.innerHTML = `
            <span class="spinner-border spinner-border-sm"></span>
            Savdo saqlanmoqda...
        `;

        updatePayment();

        try {
            const response = await fetch(
                checkoutUrl,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: JSON.stringify({
                        items,
                        payment_method: paymentMethod,
                        amount_received: amountReceived,
                    }),
                }
            );

            const data = await response.json();

            if (!response.ok || !data.ok) {
                throw new Error(
                    flattenErrors(data.errors)
                );
            }

            successSaleNumber.textContent = (
                data.sale.sale_number
            );

            successTotal.textContent = formatMoney(
                data.sale.total
            );

            successReceived.textContent = formatMoney(
                data.sale.amount_received
            );

            successChange.textContent = formatMoney(
                data.sale.change_amount
            );

            successOverlay.classList.add(
                "is-visible"
            );

            successOverlay.setAttribute(
                "aria-hidden",
                "false"
            );

            cart.clear();
            amountReceivedInput.value = "";

            renderCart();
            loadProducts();

        } catch (error) {
            showCheckoutError(
                error.message
                || "Savdoni yakunlab bo‘lmadi."
            );

        } finally {
            isSubmitting = false;

            checkoutButton.innerHTML = `
                <i class="bi bi-check-circle"></i>
                <span>Savdoni yakunlash</span>
            `;

            updatePayment();
        }
    }

    productResults.addEventListener(
        "click",
        (event) => {
            const productButton = event.target.closest(
                "[data-product-id]"
            );

            if (!productButton) {
                return;
            }

            const product = searchProducts.get(
                productButton.dataset.productId
            );

            if (product) {
                addProduct(product);
            }
        }
    );

    cartItems.addEventListener(
        "click",
        (event) => {
            const actionButton = event.target.closest(
                "button[data-action]"
            );

            if (!actionButton) {
                return;
            }

            const productId = Number(
                actionButton.dataset.productId
            );

            const item = cart.get(productId);

            if (!item) {
                return;
            }

            const action = actionButton.dataset.action;

            if (action === "remove") {
                cart.delete(productId);
                renderCart();

                return;
            }

            const step = (
                item.product.unit === "piece"
                    ? 1
                    : 0.1
            );

            if (action === "increase") {
                changeCartQuantity(
                    productId,
                    item.quantity + step
                );

                return;
            }

            if (action === "decrease") {
                const newQuantity = (
                    item.quantity - step
                );

                if (newQuantity <= 0) {
                    cart.delete(productId);
                    renderCart();

                    return;
                }

                changeCartQuantity(
                    productId,
                    newQuantity
                );
            }
        }
    );

    cartItems.addEventListener(
        "change",
        (event) => {
            if (
                event.target.dataset.action
                !== "quantity"
            ) {
                return;
            }

            changeCartQuantity(
                Number(event.target.dataset.productId),
                parseNumber(event.target.value)
            );
        }
    );

    searchInput.addEventListener(
        "input",
        () => {
            window.clearTimeout(searchTimer);

            searchTimer = window.setTimeout(
                () => {
                    loadProducts();
                },
                250
            );
        }
    );

    searchInput.addEventListener(
        "keydown",
        (event) => {
            if (event.key !== "Enter") {
                return;
            }

            event.preventDefault();

            window.clearTimeout(searchTimer);

            loadProducts({
                addExact: true,
            });
        }
    );

    document.querySelectorAll(
        'input[name="payment_method"]'
    ).forEach((input) => {
        input.addEventListener(
            "change",
            () => {
                clearCheckoutError();
                updatePayment();
            }
        );
    });

    amountReceivedInput.addEventListener(
        "input",
        () => {
            clearCheckoutError();
            updatePayment();
        }
    );

    exactCashButton.addEventListener(
        "click",
        () => {
            amountReceivedInput.value = (
                calculateTotal().toFixed(2)
            );

            updatePayment();
        }
    );

    document.querySelectorAll(
        "[data-cash-value]"
    ).forEach((button) => {
        button.addEventListener(
            "click",
            () => {
                amountReceivedInput.value = (
                    button.dataset.cashValue
                );

                updatePayment();
            }
        );
    });

    checkoutButton.addEventListener(
        "click",
        submitCheckout
    );

    startNextSaleButton.addEventListener(
        "click",
        () => {
            successOverlay.classList.remove(
                "is-visible"
            );

            successOverlay.setAttribute(
                "aria-hidden",
                "true"
            );

            searchInput.value = "";
            searchInput.focus();

            loadProducts();
        }
    );

    document.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Escape"
                && successOverlay.classList.contains(
                    "is-visible"
                )
            ) {
                startNextSaleButton.click();
            }
        }
    );

    renderCart();
    loadProducts();
})();