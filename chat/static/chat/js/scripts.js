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