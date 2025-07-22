// JavaScript for Animal Explorer

function setAnimal(animal) {
    const input = document.getElementById('animal');
    if (input) {
        // Add typing animation effect
        input.value = '';
        input.focus();
        
        let i = 0;
        const typeWriter = () => {
            if (i < animal.length) {
                input.value += animal.charAt(i);
                i++;
                setTimeout(typeWriter, 50);
            }
        };
        
        typeWriter();
        
        // Add visual feedback to the clicked tag
        const tags = document.querySelectorAll('.tag');
        tags.forEach(tag => {
            if (tag.textContent.includes(animal)) {
                tag.style.transform = 'scale(1.1)';
                setTimeout(() => {
                    tag.style.transform = '';
                }, 200);
            }
        });
    }
}

function showTab(tabName) {
    // Hide all tab contents
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.style.display = 'none');
    
    // Show selected tab
    const selectedTab = document.getElementById(tabName + '-tab');
    if (selectedTab) {
        selectedTab.style.display = 'block';
    }
    
    // Update active tab button
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => btn.classList.remove('active'));
    
    const activeBtn = document.querySelector(`[onclick="showTab('${tabName}')"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
}

function showRateLimitCountdown() {
    const countdownElement = document.getElementById('rate-limit-countdown');
    if (!countdownElement) return;
    
    // Start with a 60-second countdown (for minute limit)
    let secondsRemaining = 60;
    
    function updateCountdown() {
        const minutes = Math.floor(secondsRemaining / 60);
        const seconds = secondsRemaining % 60;
        
        if (secondsRemaining > 0) {
            countdownElement.innerHTML = `⏱️ Podrás intentar de nuevo en: ${minutes}:${seconds.toString().padStart(2, '0')}`;
            secondsRemaining--;
        } else {
            countdownElement.innerHTML = '✅ ¡Ya puedes hacer una nueva consulta!';
            countdownElement.classList.add('expired');
            
            // Add button to try again
            countdownElement.innerHTML += '<br><button class="btn-primary" onclick="window.location.href=\'/\'" style="margin-top: 15px;">🔄 Intentar de Nuevo</button>';
            clearInterval(countdownTimer);
        }
    }
    
    // Update countdown every second
    updateCountdown();
    const countdownTimer = setInterval(updateCountdown, 1000);
}

async function checkRateLimits() {
    try {
        const response = await fetch('/api/rate-limits');
        const data = await response.json();
        
        if (data.status === 'info' && data.limits) {
            console.log('Rate limits status:', data.limits);
            
            // Show remaining limits in console for debugging
            const { minute, hour, day } = data.limits;
            console.log(`Remaining: ${minute.remaining}/min, ${hour.remaining}/hour, ${day.remaining}/day`);
        }
        
        return data;
    } catch (error) {
        console.error('Error checking rate limits:', error);
        return null;
    }
}

function pollResults() {
    if (typeof sessionId === 'undefined') {
        console.error('Session ID not defined');
        return;
    }
    
    const poll = async () => {
        try {
            const response = await fetch(`/status/${sessionId}`);
            if (!response.ok) {
                throw new Error(`Error: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Manejar caso especial para recargas
            if (data.status === 'reload_required') {
                showError(data.message || 'Se requiere recarga para ver los resultados');
                document.getElementById('new-search-btn').style.display = 'inline-block';
                return; // Detener polling
            }
            
            updateProgress(data);
            
            if (data.status === 'completed' || data.status === 'error' || data.status === 'invalid_animal') {
                displayResults(data);
                return; // Detener polling
            }
            
            // Continuar polling
            setTimeout(poll, 1000);
            
        } catch (error) {
            console.error('Polling error:', error);
            showError('Error de conexión. Por favor, recarga la página.');
        }
    };
    
    poll();
}

function updateProgress(data) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    if (!progressFill || !progressText) return;
    
    let progress = 0;
    let text = '';
    
    switch (data.status) {
        case 'processing':
            progress = 10;
            text = 'Iniciando investigación...';
            break;
        case 'getting_info':
            progress = 30;
            text = 'Consultando información del animal...';
            break;
        case 'generating_image':
            progress = 70;
            text = 'Generando imagen con IA...';
            break;
        case 'completed':
            progress = 100;
            text = '¡Investigación completada!';
            break;
        case 'invalid_animal':
            progress = 100;
            text = 'Validación completada';
            break;
        case 'error':
            progress = 100;
            text = 'Error en el procesamiento';
            break;
        default:
            progress = 0;
            text = 'Preparando...';
    }
    
    progressFill.style.width = progress + '%';
    progressText.textContent = text;
}

function displayResults(data) {
    const progressSection = document.getElementById('progress-section');
    const resultsSection = document.getElementById('results');
    const errorSection = document.getElementById('error-section');
    const newSearchBtn = document.getElementById('new-search-btn');
    
    // Hide progress
    if (progressSection) {
        progressSection.style.display = 'none';
    }
    
    // Show new search button
    if (newSearchBtn) {
        newSearchBtn.style.display = 'inline-block';
    }
    
    // Display info if available
    if (data.info) {
        const infoDiv = document.getElementById('animal-info');
        if (infoDiv) {
            renderAnimalInfo(infoDiv, data.info);
        }
    }
    
    // Display image if available
    if (data.image) {
        const imageContainer = document.getElementById('image-container');
        const downloadBtn = document.getElementById('download-btn');
        
        if (imageContainer) {
            imageContainer.innerHTML = `
                <img src="${data.image}" alt="Imagen generada de ${animal}" class="generated-image">
            `;
            
            // Show download button
            if (downloadBtn) {
                downloadBtn.style.display = 'inline-block';
                downloadBtn.setAttribute('data-image-url', data.image);
            }
        }
    }
    
    // Show results if we have info or image
    if ((data.info || data.image) && resultsSection) {
        resultsSection.style.display = 'block';
    }
    
    // Display errors if any
    if (data.errors && data.errors.length > 0) {
        const errorList = document.getElementById('error-list');
        if (errorList && errorSection) {
            errorList.innerHTML = '';
            data.errors.forEach(error => {
                const li = document.createElement('li');
                li.innerHTML = error.replace(/\n/g, '<br>'); // Allow line breaks in error messages
                errorList.appendChild(li);
            });
            
            // Add suggestions as clickable buttons if available
            if (data.suggestions && data.suggestions.length > 0) {
                const suggestionsDiv = document.createElement('div');
                suggestionsDiv.className = 'suggestions-container';
                suggestionsDiv.innerHTML = '<h4>💡 Sugerencias:</h4>';
                
                data.suggestions.forEach(suggestion => {
                    const suggestionBtn = document.createElement('button');
                    suggestionBtn.className = 'btn-suggestion';
                    suggestionBtn.textContent = suggestion;
                    suggestionBtn.onclick = () => {
                        // Redirect to home with pre-filled suggestion
                        window.location.href = `/?animal=${encodeURIComponent(suggestion)}`;
                    };
                    suggestionsDiv.appendChild(suggestionBtn);
                });
                
                errorList.appendChild(suggestionsDiv);
            }
            
            errorSection.style.display = 'block';
        }
    }
}

function downloadImage() {
    const downloadBtn = document.getElementById('download-btn');
    const imageDataUrl = downloadBtn.getAttribute('data-image-url');
    
    if (imageDataUrl) {
        const link = document.createElement('a');
        link.href = imageDataUrl;
        link.download = `${animal}_generated_image.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

function showError(message) {
    const errorSection = document.getElementById('error-section');
    const errorList = document.getElementById('error-list');
    
    if (errorList && errorSection) {
        errorList.innerHTML = `<li>${message}</li>`;
        errorSection.style.display = 'block';
    }
}

// Handle form submission
function renderAnimalInfo(container, text) {
    container.innerHTML = ''; // Clear previous content
    const items = text.split('**').filter(s => s.trim() !== '');

    for (let i = 0; i < items.length; i += 2) {
        const label = items[i].replace(':', '').trim();
        const value = items[i + 1] ? items[i + 1].trim() : '';

        if (label && value) {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'info-item';

            const labelSpan = document.createElement('span');
            labelSpan.className = 'info-label';
            labelSpan.textContent = label;

            const valueSpan = document.createElement('span');
            valueSpan.className = 'info-value';
            valueSpan.textContent = value;

            itemDiv.appendChild(labelSpan);
            itemDiv.appendChild(valueSpan);
            container.appendChild(itemDiv);
        }
    }
}

// Enhanced form submission with loading animation
function handleFormSubmit(form) {
    const submitBtn = document.getElementById('submitBtn');
    const input = document.getElementById('animal');
    
    if (!input.value.trim()) {
        // Enhanced error notification
        showNotification('Por favor ingresa el nombre de un animal.', 'warning');
        input.focus();
        input.classList.add('shake');
        setTimeout(() => input.classList.remove('shake'), 500);
        return false;
    }
    
    // Add loading state to button
    if (submitBtn) {
        submitBtn.classList.add('loading');
        submitBtn.disabled = true;
    }
    
    // Add loading class to input
    input.classList.add('loading');
    input.disabled = true;
    
    return true;
}

// Enhanced notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">${getNotificationIcon(type)}</span>
            <span class="notification-message">${message}</span>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Add entrance animation
    setTimeout(() => notification.classList.add('show'), 100);
    
    // Auto remove after 4 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

function getNotificationIcon(type) {
    const icons = {
        info: 'ℹ️',
        success: '✅',
        warning: '⚠️',
        error: '❌'
    };
    return icons[type] || icons.info;
}

// Shuffle tags with enhanced animation
function shuffleTags() {
    const allAnimals = [
        {name: 'Jaguar', emoji: '🐆'}, {name: 'Koala', emoji: '🐨'}, 
        {name: 'Medusa', emoji: '🔴'}, {name: 'Pulpo', emoji: '🐙'},
        {name: 'Gecko', emoji: '🦎'}, {name: 'Flamingo', emoji: '🦩'},
        {name: 'Nutria', emoji: '🦦'}, {name: 'Loro', emoji: '🦜'},
        {name: 'Panda', emoji: '🐼'}, {name: 'Rana', emoji: '🐸'},
        {name: 'Ballena', emoji: '🐋'}, {name: 'Búho', emoji: '🦉'},
        {name: 'Canguro', emoji: '🦘'}, {name: 'Zebra', emoji: '🦓'}
    ];
    
    const tags = document.querySelectorAll('.tag');
    const shuffleBtn = document.querySelector('.btn-shuffle');
    
    // Disable button during animation
    if (shuffleBtn) {
        shuffleBtn.disabled = true;
        shuffleBtn.style.transform = 'scale(0.95)';
    }
    
    tags.forEach((tag, index) => {
        setTimeout(() => {
            const randomAnimal = allAnimals[Math.floor(Math.random() * allAnimals.length)];
            const emoji = tag.querySelector('.tag-emoji');
            const text = tag.querySelector('.tag-text');
            
            // Flip animation
            tag.style.transform = 'rotateY(90deg) scale(0.8)';
            
            setTimeout(() => {
                if (emoji) emoji.textContent = randomAnimal.emoji;
                if (text) text.textContent = randomAnimal.name;
                tag.onclick = () => setAnimal(randomAnimal.name);
                
                // Flip back
                tag.style.transform = 'rotateY(0deg) scale(1)';
            }, 200);
        }, index * 100);
    });
    
    // Re-enable shuffle button
    setTimeout(() => {
        if (shuffleBtn) {
            shuffleBtn.disabled = false;
            shuffleBtn.style.transform = '';
        }
    }, tags.length * 100 + 400);
}

// Enhanced search with suggestions
function initEnhancedSearch() {
    const input = document.getElementById('animal');
    const suggestions = document.getElementById('searchSuggestions');
    
    if (!input || !suggestions) return;
    
    const commonAnimals = [
        'León', 'Tigre', 'Elefante', 'Jirafa', 'Cebra', 'Hipopótamo',
        'Rinoceronte', 'Cocodrilo', 'Serpiente', 'Águila', 'Halcón',
        'Búho', 'Loro', 'Pingüino', 'Delfín', 'Ballena', 'Tiburón',
        'Pulpo', 'Medusa', 'Rana', 'Salamandra', 'Iguana', 'Gecko'
    ];
    
    input.addEventListener('input', function() {
        const value = this.value.toLowerCase();
        
        if (value.length < 2) {
            suggestions.style.display = 'none';
            return;
        }
        
        const matches = commonAnimals.filter(animal => 
            animal.toLowerCase().includes(value)
        ).slice(0, 5);
        
        if (matches.length === 0) {
            suggestions.style.display = 'none';
            return;
        }
        
        suggestions.innerHTML = matches.map(animal => 
            `<div class="suggestion-item" onclick="selectSuggestion('${animal}')">${animal}</div>`
        ).join('');
        
        suggestions.style.display = 'block';
    });
    
    // Hide suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !suggestions.contains(e.target)) {
            suggestions.style.display = 'none';
        }
    });
}

function selectSuggestion(animal) {
    const input = document.getElementById('animal');
    const suggestions = document.getElementById('searchSuggestions');
    
    if (input) {
        setAnimal(animal);
    }
    
    if (suggestions) {
        suggestions.style.display = 'none';
    }
}

// Populate popular animals section
function loadPopularAnimals() {
    const popularGrid = document.getElementById('popularAnimals');
    if (!popularGrid) return;
    
    const popularAnimals = [
        'León 🦁', 'Delfín 🐬', 'Águila 🦅', 'Elefante 🐘',
        'Tigre 🐅', 'Pingüino 🐧', 'Mariposa 🦋', 'Tiburón 🦈'
    ];
    
    popularGrid.innerHTML = popularAnimals.map((animal, index) => {
        const name = animal.split(' ')[0];
        return `
            <div class="popular-item" onclick="setAnimal('${name}')" style="animation-delay: ${index * 0.1}s">
                ${animal}
            </div>
        `;
    }).join('');
}

document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.search-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!handleFormSubmit(form)) {
                e.preventDefault();
            }
        });
    }
    
    // Initialize enhanced features
    initEnhancedSearch();
    loadPopularAnimals();
    
    // Pre-fill input if animal parameter is provided in URL
    const urlParams = new URLSearchParams(window.location.search);
    const animalParam = urlParams.get('animal');
    if (animalParam) {
        const input = document.getElementById('animal');
        if (input) {
            input.value = animalParam;
            input.focus();
        }
    }
    
    // Add enhanced interactions
    const input = document.getElementById('animal');
    if (input) {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    }
    
    // Initialize floating animations with stagger
    const elements = document.querySelectorAll('.feature, .tag, .stat-item');
    elements.forEach((el, index) => {
        el.style.animationDelay = `${index * 0.1}s`;
    });
});
