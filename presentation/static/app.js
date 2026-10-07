let currentMode = 'keyword';
let allProducts = [];
let queryImageEmbedding = null;
let queryImageName = null;
let recognition = null;
let isRecording = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  checkDbStatus();
  loadAllProducts();
  loadAllOrders();
  loadEvaluationSuite();
  setupSpeechRecognition();

  // Enter key in search input
  document.getElementById('searchInput').addEventListener('keyup', (e) => {
    if (e.key === 'Enter') {
      executeSearch();
    }
  });

  // Enter key in order input
  document.getElementById('orderInput').addEventListener('keyup', (e) => {
    if (e.key === 'Enter') {
      lookupOrder();
    }
  });
});

// TAB SWITCHING
function switchTab(tabName) {
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

  if (tabName === 'products') {
    document.getElementById('tabProducts').classList.add('active');
    document.getElementById('tabProductsBtn').classList.add('active');
  } else if (tabName === 'orders') {
    document.getElementById('tabOrders').classList.add('active');
    document.getElementById('tabOrdersBtn').classList.add('active');
  } else if (tabName === 'architecture') {
    document.getElementById('tabArchitecture').classList.add('active');
    document.getElementById('tabArchBtn').classList.add('active');
  }
}

// SEARCH MODES
function setSearchMode(mode) {
  currentMode = mode;
  document.querySelectorAll('.mode-pill').forEach(btn => btn.classList.remove('active'));

  const modeBtnMap = {
    keyword: 'modeKeyword',
    voice: 'modeVoice',
    image: 'modeImage',
    multimodal: 'modeMultimodal'
  };
  if (modeBtnMap[mode]) {
    document.getElementById(modeBtnMap[mode]).classList.add('active');
  }

  const searchInput = document.getElementById('searchInput');
  const fusionSlider = document.getElementById('fusionSliderGroup');
  const imgBox = document.getElementById('imagePreviewBox');

  if (mode === 'keyword') {
    searchInput.placeholder = "Enter keyword (e.g. 'black running shoes', 'leather bag')...";
    fusionSlider.style.display = 'none';
  } else if (mode === 'voice') {
    searchInput.placeholder = "Voice search: speak or type spoken query (e.g. 'find running shoes')...";
    fusionSlider.style.display = 'none';
  } else if (mode === 'image') {
    searchInput.placeholder = "Image search active. Choose an image prototype or upload file below...";
    fusionSlider.style.display = 'none';
    if (!queryImageEmbedding) {
      changeImagePreset();
    }
    imgBox.style.display = 'flex';
  } else if (mode === 'multimodal') {
    searchInput.placeholder = "Enter text keywords (e.g. 'running') to fuse with image embedding...";
    fusionSlider.style.display = 'flex';
    if (!queryImageEmbedding) {
      changeImagePreset();
    }
    imgBox.style.display = 'flex';
  }
}

// WEB SPEECH RECOGNITION (Use Case: Search by Voice)
function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      isRecording = true;
      document.getElementById('micBtn').classList.add('recording');
      document.getElementById('voiceStatusBox').style.display = 'flex';
      document.getElementById('voiceStatusText').innerText = "Listening... Speak your search query.";
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      document.getElementById('searchInput').value = transcript;
      stopVoiceRecording();
      setSearchMode('voice');
      executeSearch();
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      stopVoiceRecording();
      alert("Could not capture audio or microphone permission was denied. You can type simulated voice input directly.");
    };

    recognition.onend = () => {
      stopVoiceRecording();
    };
  }
}

function toggleVoiceInput() {
  if (!recognition) {
    const simulated = prompt("Speech API is unavailable. Enter simulated voice query:", "find running shoes");
    if (simulated) {
      document.getElementById('searchInput').value = simulated;
      setSearchMode('voice');
      executeSearch();
    }
    return;
  }

  if (isRecording) {
    recognition.stop();
  } else {
    try {
      recognition.start();
    } catch (e) {
      console.error(e);
    }
  }
}

function stopVoiceRecording() {
  isRecording = false;
  document.getElementById('micBtn').classList.remove('recording');
  document.getElementById('voiceStatusBox').style.display = 'none';
  if (recognition) {
    try { recognition.stop(); } catch (e) {}
  }
}

// IMAGE UPLOAD & PROTOTYPES (Use Case: Search by Image)
function triggerImageUpload() {
  document.getElementById('imageFileInput').click();
}

function handleImageFileSelected(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (uploadEvent) => {
    document.getElementById('imagePreviewThumb').src = uploadEvent.target.result;
    document.getElementById('imagePreviewName').innerText = file.name;
    document.getElementById('imagePreviewBox').style.display = 'flex';

    // Map to simulated visual prototype embedding based on filename
    const lowerName = file.name.toLowerCase();
    if (lowerName.includes('bag') || lowerName.includes('leather')) {
      queryImageEmbedding = [0.1, 0.2, 0.9];
      document.getElementById('imagePresetSelect').value = 'bag';
    } else if (lowerName.includes('tshirt') || lowerName.includes('shirt') || lowerName.includes('cloth')) {
      queryImageEmbedding = [0.3, 0.7, 0.4];
      document.getElementById('imagePresetSelect').value = 'clothing';
    } else if (lowerName.includes('watch')) {
      queryImageEmbedding = [0.4, 0.5, 0.6];
      document.getElementById('imagePresetSelect').value = 'watch';
    } else {
      queryImageEmbedding = [0.9, 0.1, 0.2];
      document.getElementById('imagePresetSelect').value = 'shoes';
    }

    if (currentMode === 'keyword') {
      setSearchMode('image');
    }
  };
  reader.readAsDataURL(file);
}

function changeImagePreset() {
  const preset = document.getElementById('imagePresetSelect').value;
  const presets = {
    shoes: { emb: [0.9, 0.1, 0.2], label: 'Shoes Prototype', img: '/images/nike_running_black.svg' },
    running_shoes: { emb: [0.9, 0.15, 0.15], label: 'Running Shoes', img: '/images/adidas_running_white.svg' },
    bag: { emb: [0.1, 0.2, 0.9], label: 'Leather Bag', img: '/images/black_leather_bag.svg' },
    clothing: { emb: [0.3, 0.7, 0.4], label: 'Casual Apparel', img: '/images/white_casual_tshirt.svg' },
    watch: { emb: [0.4, 0.5, 0.6], label: 'Smart Watch', img: '/images/smart_fitness_watch.svg' }
  };

  const selected = presets[preset] || presets.shoes;
  queryImageEmbedding = selected.emb;
  document.getElementById('imagePreviewThumb').src = selected.img;
  document.getElementById('imagePreviewName').innerText = selected.label;
  document.getElementById('imagePreviewBox').style.display = 'flex';
}

function clearImageQuery() {
  queryImageEmbedding = null;
  document.getElementById('imagePreviewBox').style.display = 'none';
  if (currentMode === 'image') {
    setSearchMode('keyword');
  }
}

function updateFusionWeight(val) {
  const textPct = val;
  const imgPct = 100 - val;
  document.getElementById('weightLabel').innerText = `${textPct}% Text / ${imgPct}% Image`;
}

// QUICK SEARCH TAGS
function quickSearch(query) {
  document.getElementById('searchInput').value = query;
  setSearchMode('keyword');
  executeSearch();
}

// EXECUTE SEARCH (Calls Flask API)
async function executeSearch() {
  const searchInput = document.getElementById('searchInput').value.trim();
  const applyRanking = document.getElementById('rankingBoostToggle').checked;

  let endpoint = '/api/search/text';
  let payload = { query: searchInput, apply_ranking: applyRanking };

  if (currentMode === 'voice') {
    endpoint = '/api/search/voice';
    payload = { audio_text: searchInput, apply_ranking: applyRanking };
  } else if (currentMode === 'image') {
    if (!queryImageEmbedding) {
      changeImagePreset();
    }
    endpoint = '/api/search/image';
    payload = { embedding: queryImageEmbedding, apply_ranking: applyRanking };
  } else if (currentMode === 'multimodal') {
    if (!queryImageEmbedding) {
      changeImagePreset();
    }
    const val = parseInt(document.getElementById('fusionWeight').value, 10);
    const lambdaT = val / 100.0;
    const lambdaI = (100 - val) / 100.0;
    endpoint = '/api/search/multimodal';
    payload = {
      text: searchInput,
      embedding: queryImageEmbedding,
      lambda_t: lambdaT,
      lambda_i: lambdaI,
      apply_ranking: applyRanking
    };
  }

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    renderProducts(data.results, data.mode_title || `Search Results`);
  } catch (err) {
    console.error("Search failed:", err);
  }
}

// LOAD ALL PRODUCTS
async function loadAllProducts() {
  try {
    const res = await fetch('/api/products');
    const data = await res.json();
    allProducts = data.products;
    renderProducts(allProducts.map(p => ({ product: p, score: null })), "All Products");
  } catch (e) {
    console.error("Failed to load products:", e);
  }
}

// RENDER PRODUCTS GRID (Presentation Component: SearchResultView)
function renderProducts(items, title) {
  const grid = document.getElementById('productsGrid');
  const heading = document.getElementById('resultsHeading');
  const sub = document.getElementById('resultsSub');

  heading.innerText = title;
  sub.innerText = `Found ${items.length} product(s)`;

  if (!items || items.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 48px 0; color: #64748b;">
        <p style="font-size: 1.2rem; font-weight: 600;">No matching products found.</p>
        <p style="font-size: 0.9rem;">Try different keywords, an image prototype, or clear filters.</p>
        <button class="btn btn-sm" style="margin-top: 12px;" onclick="loadAllProducts()">Reset View</button>
      </div>
    `;
    return;
  }

  grid.innerHTML = items.map(({ product, score }) => {
    const inStock = product.stock > 0;
    const stockBadge = inStock 
      ? `<span class="badge badge-instock">In Stock (${product.stock})</span>`
      : `<span class="badge badge-outstock">Out of Stock</span>`;

    const scoreBadge = (score !== null && score !== undefined)
      ? `<div class="score-badge">Score: ${score}</div>`
      : '';

    const imgSrc = product.image ? `/${product.image}` : '/images/nike_running_black.svg';

    return `
      <div class="product-card" onclick="viewProduct(${product.id})">
        <div class="card-img-wrapper">
          <img src="${imgSrc}" alt="${product.name}" onerror="this.src='/images/nike_running_black.svg'">
          ${scoreBadge}
        </div>
        <div class="card-body">
          <div class="card-meta">
            <span class="badge badge-cat">${product.category}</span>
            <span class="badge badge-color">${product.color}</span>
            ${stockBadge}
          </div>
          <h3 class="card-title">${product.name}</h3>
          <p class="card-desc">${product.description || ''}</p>
          <div class="card-footer">
            <span class="card-price">$${product.price}</span>
            <button class="card-btn" onclick="event.stopPropagation(); viewProduct(${product.id})">View Details</button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// FILTER BY CATEGORY
function filterByCategory() {
  const cat = document.getElementById('categoryFilter').value;
  if (cat === 'all') {
    renderProducts(allProducts.map(p => ({ product: p, score: null })), "All Products");
  } else {
    const filtered = allProducts
      .filter(p => p.category.toLowerCase() === cat.toLowerCase())
      .map(p => ({ product: p, score: null }));
    renderProducts(filtered, `Category: ${cat.toUpperCase()}`);
  }
}

// VIEW PRODUCT MODAL (Use Case: View product)
async function viewProduct(productId) {
  try {
    const res = await fetch(`/api/product/${productId}`);
    const data = await res.json();
    if (!data.product) return;

    const p = data.product;
    const imgSrc = p.image ? `/${p.image}` : '/images/nike_running_black.svg';
    const embChips = (p.embedding || []).map(val => `<span class="emb-chip">${val}</span>`).join('');

    const modalContent = `
      <div class="modal-img-wrap">
        <img src="${imgSrc}" alt="${p.name}" onerror="this.src='/images/nike_running_black.svg'">
      </div>
      <div class="card-meta" style="margin-bottom: 12px;">
        <span class="badge badge-cat">${p.category}</span>
        <span class="badge badge-color">${p.color}</span>
        <span class="badge ${p.stock > 0 ? 'badge-instock' : 'badge-outstock'}">
          ${p.stock > 0 ? `Stock: ${p.stock}` : 'Out of Stock'}
        </span>
      </div>
      <h2 style="font-size: 1.4rem; margin-bottom: 8px;">${p.name}</h2>
      <div style="font-size: 1.3rem; font-weight: 800; color: #2563eb; margin-bottom: 16px;">$${p.price}</div>
      <p style="color: #475569; font-size: 0.95rem; line-height: 1.6; margin-bottom: 20px;">
        ${p.description}
      </p>
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 20px;">
        <label style="font-size: 0.75rem; text-transform: uppercase; font-weight: 700; color: #64748b;">
          Vector Embedding f_theta(I)
        </label>
        <div class="embedding-chip-list">
          ${embChips}
        </div>
      </div>
      <div style="display: flex; gap: 10px;">
        <button class="btn btn-primary" onclick="searchSimilarImage(${p.id})">🔍 Find Visually Similar</button>
        <button class="btn btn-sm" onclick="closeProductModal()">Close</button>
      </div>
    `;

    document.getElementById('modalProductContent').innerHTML = modalContent;
    document.getElementById('productModal').classList.add('open');
  } catch (err) {
    console.error("View product error:", err);
  }
}

function closeProductModal(event) {
  if (!event || event.target === document.getElementById('productModal') || event.target.classList.contains('modal-close-btn')) {
    document.getElementById('productModal').classList.remove('open');
  }
}

function searchSimilarImage(productId) {
  closeProductModal();
  const prod = allProducts.find(p => p.id === productId);
  if (prod && prod.embedding) {
    queryImageEmbedding = prod.embedding;
    document.getElementById('imagePreviewThumb').src = `/${prod.image}`;
    document.getElementById('imagePreviewName').innerText = `${prod.name} (Vector)`;
    document.getElementById('imagePreviewBox').style.display = 'flex';
    setSearchMode('image');
    executeSearch();
  }
}

// ORDER TRACKING (Use Case: Search Order & View Order)
async function lookupOrder(orderIdInput) {
  const orderId = orderIdInput || document.getElementById('orderInput').value.trim();
  if (!orderId) {
    alert("Please enter an Order ID.");
    return;
  }

  try {
    const res = await fetch(`/api/order/${orderId}`);
    const data = await res.json();
    const resultBox = document.getElementById('orderResultDisplay');

    if (!data.order) {
      resultBox.style.display = 'block';
      resultBox.innerHTML = `
        <div style="color: #dc2626; font-weight: 600;">
          ❌ Order '${orderId}' not found in the database.
        </div>
      `;
      return;
    }

    const ord = data.order;
    let statusClass = 'status-shipped';
    const st = ord.status.toLowerCase();
    if (st.includes('deliver') && !st.includes('out')) statusClass = 'status-delivered';
    else if (st.includes('process')) statusClass = 'status-processing';
    else if (st.includes('out')) statusClass = 'status-delivery';

    const itemsHtml = (ord.items || []).map(it => `
      <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #e2e8f0; font-size: 0.9rem;">
        <span>Product ID: <strong>#${it.product_id}</strong> &times; ${it.quantity}</span>
        <span style="font-weight: 600;">$${it.price * it.quantity}</span>
      </div>
    `).join('');

    resultBox.style.display = 'block';
    resultBox.innerHTML = `
      <div class="order-details-header">
        <div>
          <h3 style="font-size: 1.25rem;">Order #${ord.order_id}</h3>
          <span style="font-size: 0.85rem; color: #64748b;">Customer: ${ord.customer_id} • Date: ${ord.date || 'N/A'}</span>
        </div>
        <span class="status-badge ${statusClass}">${ord.status}</span>
      </div>
      <div class="order-meta-grid">
        <div class="order-meta-item">
          <label>Status</label>
          <span>${ord.status}</span>
        </div>
        <div class="order-meta-item">
          <label>Total Price</label>
          <span style="color: #16a34a; font-size: 1.15rem;">$${ord.total}</span>
        </div>
      </div>
      <div style="margin-top: 16px;">
        <label style="font-size: 0.75rem; text-transform: uppercase; font-weight: 700; color: #64748b;">Itemized Products</label>
        ${itemsHtml || '<p style="font-size: 0.85rem; color: #64748b;">No individual items listed.</p>'}
      </div>
    `;
  } catch (err) {
    console.error("Order lookup failed:", err);
  }
}

function quickOrder(oid) {
  document.getElementById('orderInput').value = oid;
  lookupOrder(oid);
}

// LOAD ALL ORDERS
async function loadAllOrders() {
  try {
    const res = await fetch('/api/orders');
    const data = await res.json();
    const tbody = document.getElementById('allOrdersTbody');
    if (!tbody || !data.orders) return;

    tbody.innerHTML = data.orders.map(o => `
      <tr>
        <td style="font-family: 'JetBrains Mono', monospace; font-weight: 600;">${o.order_id}</td>
        <td>${o.customer_id}</td>
        <td>${o.date || 'N/A'}</td>
        <td><span class="status-badge status-shipped" style="font-size: 0.7rem;">${o.status}</span></td>
        <td>${(o.items || []).length} item(s)</td>
        <td style="font-weight: 700; color: #16a34a;">$${o.total}</td>
        <td><button class="btn btn-sm" onclick="quickOrder('${o.order_id}')">View</button></td>
      </tr>
    `).join('');
  } catch (e) {
    console.error("Failed to load orders:", e);
  }
}

// EVALUATION SUITE
async function loadEvaluationSuite() {
  try {
    const res = await fetch('/api/evaluation');
    const data = await res.json();
    const tbody = document.getElementById('evalTableTbody');
    const metricsDiv = document.getElementById('evalMetrics');
    if (!tbody || !data.evaluation) return;

    tbody.innerHTML = data.evaluation.map(row => `
      <tr>
        <td style="font-family: 'JetBrains Mono', monospace;">${row.query}</td>
        <td><span class="badge badge-cat">${row.mode}</span></td>
        <td style="font-weight: 600;">${row.top1_result}</td>
        <td style="font-family: 'JetBrains Mono', monospace;">${row.score !== undefined ? row.score : 'N/A'}</td>
        <td>
          <span class="badge ${row.success ? 'badge-instock' : 'badge-outstock'}">
            ${row.success ? '✓ Yes' : '✗ No'}
          </span>
        </td>
      </tr>
    `).join('');

    metricsDiv.innerHTML = `
      Total Test Queries: <strong>${data.total}</strong> | 
      Successful: <strong>${data.successful}</strong> | 
      Success Rate: <strong>${data.success_rate}%</strong>
    `;
  } catch (e) {
    console.error("Failed to load evaluation:", e);
  }
}

// DATABASE STATUS CHECK
async function checkDbStatus() {
  try {
    const res = await fetch('/api/db/status');
    const data = await res.json();
    const badge = document.getElementById('dbStatusBadge');
    const dot = document.getElementById('dbStatusDot');
    const text = document.getElementById('dbStatusText');
    if (!badge || !dot || !text) return;

    if (data.connected) {
      dot.style.background = '#10b981';
      text.innerText = `MySQL: Connected (${data.database})`;
      badge.style.background = '#ecfdf5';
      badge.style.borderColor = '#a7f3d0';
      badge.style.color = '#065f46';
      badge.title = `Connected to MySQL (${data.host}:${data.port}, database: ${data.database})`;
    } else {
      dot.style.background = '#f59e0b';
      text.innerText = 'DB: JSON Fallback';
      badge.style.background = '#fffbeb';
      badge.style.borderColor = '#fde68a';
      badge.style.color = '#92400e';
      badge.title = `MySQL not connected: ${data.message}`;
    }
  } catch (err) {
    console.warn("Could not check DB status:", err);
  }
}

