// Функция для получения CSRF токена
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Добавь обработку формы
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.querySelector('form[method="POST"]');
    const searchInput = document.querySelector('input[name="query"]');
    const resultsContainer = document.getElementById('results-container');

    if (searchForm) {
        searchForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const query = searchInput.value.trim();
            if (!query) return;

            // Показываем лоадер
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                    <div class="glass-effect rounded-3xl p-8">
                        <div class="flex items-center justify-center gap-3">
                            <div class="loading-spinner"></div>
                            <p class="text-gray-400">Ищу информацию...</p>
                        </div>
                    </div>
                `;
            }

            try {
                const formData = new FormData(searchForm);
                const response = await fetch('/api/search/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                });

                const data = await response.json();

                if (data.success) {
                    // Отображаем результат
                    displayResult(data.query, data.answer);
                } else {
                    alert('Ошибка: ' + data.error);
                }
            } catch (error) {
                alert('Ошибка сети: ' + error.message);
            }
        });
    }
});

function displayResult(query, answer) {
    const resultsContainer = document.getElementById('results-container');
    if (!resultsContainer) return;

    const html = `
        <div class="glass-effect rounded-3xl p-8 result-card">
            <div class="flex items-center gap-3 mb-6">
                <div class="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                    <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                    </svg>
                </div>
                <div>
                    <h2 class="text-xl font-semibold">Ответ AI (RAG)</h2>
                    <p class="text-sm text-gray-500">${query}</p>
                </div>
            </div>

            <div class="bg-white/5 rounded-2xl p-6 border border-white/10">
                <div class="text-gray-300 leading-relaxed whitespace-pre-wrap">${answer}</div>
            </div>

            <div class="mt-6 flex gap-3">
                <button onclick="copyAnswer('${answer.replace(/'/g, "\\'")}')"
                        class="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition">
                    📋 Копировать
                </button>
                <button onclick="location.reload()"
                        class="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition">
                🔄 Новый вопрос
                </button>
            </div>
        </div>
    `;

    resultsContainer.innerHTML = html;
}

function copyAnswer(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Скопировано!');
    });
}

// Стандартные тесты
async function runEvaluation() {
    const btn = document.getElementById('eval-btn');
    const loading = document.getElementById('eval-loading');
    const resultsDiv = document.getElementById('eval-results');

    btn.disabled = true;
    btn.classList.add('opacity-50', 'cursor-not-allowed');
    loading.classList.remove('hidden');
    resultsDiv.innerHTML = '';

    try {
        const response = await fetch('/api/run-eval-api/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();

        if (data.status === 'success') {
            renderEvalResults(data.data);
        } else {
            resultsDiv.innerHTML = `<div class="p-4 bg-red-50 text-red-700 rounded-xl border border-red-200">❌ Ошибка: ${data.message}</div>`;
        }
    } catch (error) {
        resultsDiv.innerHTML = `<div class="p-4 bg-red-50 text-red-700 rounded-xl border border-red-200"> Ошибка сети: ${error.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed');
        loading.classList.add('hidden');
    }
}

// Тест текущего вопроса
async function evaluateCurrentQuery() {
    const queryInput = document.querySelector('input[name="query"]');
    const query = queryInput ? queryInput.value.trim() : '';

    if (!query) {
        alert('⚠️ Сначала введите вопрос в поле поиска!');
        return;
    }

    const btn = document.getElementById('eval-current-btn');
    const loading = document.getElementById('eval-loading');
    const resultsDiv = document.getElementById('eval-results');

    btn.disabled = true;
    btn.classList.add('opacity-50', 'cursor-not-allowed');
    loading.classList.remove('hidden');
    resultsDiv.innerHTML = '';

    try {
        const response = await fetch('/api/evaluate-query/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query })
        });

        const data = await response.json();

        if (response.ok) {
            renderCurrentQueryResult(data);
        } else {
            resultsDiv.innerHTML = `<div class="p-4 bg-red-50 text-red-700 rounded-xl border border-red-200">❌ Ошибка: ${data.error || data.message}</div>`;
        }
    } catch (error) {
        resultsDiv.innerHTML = `<div class="p-4 bg-red-50 text-red-700 rounded-xl border border-red-200">❌ Ошибка сети: ${error.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed');
        loading.classList.add('hidden');
    }
}

// Очистка кэша
async function clearAnswersCache() {
    if (!confirm('Очистить кэш ответов?')) return;

    try {
        const response = await fetch('/api/clear-cache/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (response.ok) {
            alert('✅ Кэш очищен!');
        } else {
            alert('❌ Ошибка: ' + data.message);
        }
    } catch (error) {
        alert('❌ Ошибка сети: ' + error.message);
    }
}

// Рендер результатов стандартных тестов
function renderEvalResults(data) {
    const container = document.getElementById('eval-results');
    let html = '<div class="space-y-3">';

    data.forEach(item => {
        const score = item.score.split('/');
        const percent = (parseInt(score[0]) / parseInt(score[1])) * 100;
        const colorClass = percent >= 75 ? 'bg-green-500' : percent >= 50 ? 'bg-yellow-500' : 'bg-red-500';
        const textClass = percent >= 75 ? 'text-green-700 bg-green-50' : percent >= 50 ? 'text-yellow-700 bg-yellow-50' : 'text-red-700 bg-red-50';

        html += `
        <div class="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div class="flex justify-between items-center mb-2">
                <h4 class="font-semibold text-gray-800">${item.question}</h4>
                <span class="text-sm font-bold px-3 py-1 rounded-full ${textClass}">${item.score}</span>
            </div>
            <div class="w-full bg-gray-100 rounded-full h-2 mb-3">
                <div class="${colorClass} h-2 rounded-full transition-all duration-700" style="width: ${percent}%"></div>
            </div>
            <p class="text-sm text-gray-600 line-clamp-2">${item.answer}</p>
        </div>`;
    });

    html += '</div>';
    container.innerHTML = html;
}

// Рендер результата текущего вопроса
function renderCurrentQueryResult(data) {
    const container = document.getElementById('eval-results');
    const percent = data.percent;
    const colorClass = percent >= 75 ? 'bg-green-500' : percent >= 50 ? 'bg-yellow-500' : 'bg-red-500';
    const textClass = percent >= 75 ? 'text-green-700 bg-green-50' : percent >= 50 ? 'text-yellow-700 bg-yellow-50' : 'text-red-700 bg-red-50';

    let html = `
    <div class="bg-white rounded-xl border border-gray-200 shadow-lg overflow-hidden result-card">
        <div class="px-6 py-4 bg-gradient-to-r from-emerald-500 to-emerald-600">
            <h3 class="font-bold text-white text-lg flex items-center gap-2">
                🎯 Результат проверки вопроса
            </h3>
        </div>
        <div class="p-6 space-y-4">
            <div>
                <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Вопрос:</div>
                <div class="text-gray-800 font-medium text-lg">${data.query}</div>
            </div>

            <div>
                <div class="flex justify-between items-center mb-2">
                    <span class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Качество ответа</span>
                    <span class="text-sm font-bold px-3 py-1 rounded-full ${textClass}">${data.score}</span>
                </div>
                <div class="w-full bg-gray-100 rounded-full h-3">
                    <div class="${colorClass} h-3 rounded-full transition-all duration-700" style="width: ${percent}%"></div>
                </div>
                ${data.keywords.length > 0 ? `
                <div class="mt-2 text-sm text-gray-600">
                    Найдено: <span class="font-medium text-indigo-600">${data.found_keywords.join(', ') || 'нет'}</span> из <span class="font-medium">${data.keywords.join(', ')}</span>
                </div>` : ''}
            </div>

            <div>
                <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Ответ системы:</div>
                <div class="text-gray-700 leading-relaxed bg-gray-50 p-4 rounded-lg border border-gray-200">${data.answer}</div>
            </div>
        </div>
    </div>`;

    container.innerHTML = html;
}

// Пересборка индекса
async function rebuildIndex() {
    if (!confirm('⚠️ Пересобрать векторную базу?\n\nЭто займет 1-3 минуты. Продолжить?')) return;

    const btn = event.target.closest('button');
    const originalContent = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = `
        <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Пересборка...
    `;

    try {
        const response = await fetch('/api/rebuild/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (response.ok) {
            alert('✅ База пересобрана успешно!');
            // Очищаем кэш ответов после пересборки
            await fetch('/api/clear-cache/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            });
        } else {
            alert('❌ Ошибка: ' + data.message);
        }
    } catch (error) {
        alert('❌ Ошибка сети: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalContent;
    }
}

// Обработка формы поиска
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.querySelector('form[action*="api/search"]');
    const searchInput = document.querySelector('input[name="query"]');
    const resultsContainer = document.getElementById('results-container');

    if (searchForm) {
        searchForm.addEventListener('submit', async function(e) {
            e.preventDefault(); // Отменяем стандартную отправку

            const query = searchInput.value.trim();
            if (!query) return;

            // Показываем лоадер
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                    <div class="glass-effect rounded-3xl p-8">
                        <div class="flex items-center justify-center gap-3">
                            <div class="loading-spinner"></div>
                            <p class="text-gray-400">🔍 Ищу информацию...</p>
                        </div>
                    </div>
                `;
            }

            try {
                const formData = new FormData(searchForm);
                const response = await fetch('/api/search/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                });

                const data = await response.json();

                if (data.success) {
                    // Отображаем результат
                    displayResult(data.query, data.answer);
                } else {
                    showError(data.error || 'Ошибка при поиске');
                }
            } catch (error) {
                showError('Ошибка сети: ' + error.message);
            }
        });
    }
});

function displayResult(query, answer) {
    const resultsContainer = document.getElementById('results-container');
    if (!resultsContainer) return;

    const html = `
        <div class="glass-effect rounded-3xl p-8 result-card">
            <div class="flex items-center gap-3 mb-6">
                <div class="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                    <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                    </svg>
                </div>
                <div>
                    <h2 class="text-xl font-semibold text-white">💡 Ответ AI (RAG)</h2>
                    <p class="text-sm text-gray-400 mt-1">${escapeHtml(query)}</p>
                </div>
            </div>

            <div class="bg-white/5 rounded-2xl p-6 border border-white/10">
                <div class="text-gray-300 leading-relaxed whitespace-pre-wrap">${escapeHtml(answer)}</div>
            </div>

            <div class="mt-6 flex gap-3">
                <button onclick="copyToClipboard('${escapeHtml(answer).replace(/'/g, "\\'")}')"
                        class="px-6 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white transition flex items-center gap-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                    </svg>
                    Копировать ответ
                </button>
                <button onclick="clearSearch()"
                        class="px-6 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white transition flex items-center gap-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                    </svg>
                    Новый вопрос
                </button>
            </div>
        </div>
    `;

    resultsContainer.innerHTML = html;

    // Плавная прокрутка к результатам
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showError(message) {
    const resultsContainer = document.getElementById('results-container');
    if (!resultsContainer) return;

    resultsContainer.innerHTML = `
        <div class="glass-effect rounded-3xl p-8">
            <div class="flex items-center gap-3 text-red-400">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p>${escapeHtml(message)}</p>
            </div>
        </div>
    `;
}

function clearSearch() {
    const searchInput = document.querySelector('input[name="query"]');
    const resultsContainer = document.getElementById('results-container');

    if (searchInput) searchInput.value = '';
    if (resultsContainer) {
        resultsContainer.innerHTML = `
            <div class="glass-effect rounded-3xl p-16 text-center empty-state">
                <div class="empty-state-icon mb-4" style="font-size: 4rem; opacity: 0.5;">🔍</div>
                <p class="text-lg text-gray-400">Введите вопрос, чтобы начать поиск</p>
            </div>
        `;
    }
}

function copyToClipboard(text) {
    // Убираем HTML теги и экранирование
    const cleanText = text.replace(/<[^>]*>/g, '').replace(/\\n/g, '\n');

    navigator.clipboard.writeText(cleanText).then(() => {
        // Показываем временное уведомление
        const btn = event.target.closest('button');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '✅ Скопировано!';
        setTimeout(() => {
            btn.innerHTML = originalHTML;
        }, 2000);
    }).catch(err => {
        alert('Не удалось скопировать: ' + err);
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
