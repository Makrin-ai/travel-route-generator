/**
 * Функция для асинхронной загрузки изображений с использованием кэширования.
 * Снабжена комментариями для документации.
 */
document.addEventListener("DOMContentLoaded", function() {
    const images = document.querySelectorAll('img[data-src]');

    const options = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    /**
     * Callback для Intersection Observer. 
     * Загружает картинку только когда она появляется в поле зрения.
     */
    const handleIntersection = (entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                const src = img.getAttribute('data-src');

                // Асинхронная подгрузка
                img.src = src;
                img.onload = () => img.removeAttribute('data-src');
                
                // Прекращаем наблюдение за загруженной картинкой
                observer.unobserve(img);
            }
        });
    };

    const observer = new IntersectionObserver(handleIntersection, options);
    images.forEach(img => observer.observe(img));
});

// Функция фильтрации
function filterRoutes(routes) {
    const maxBudget = document.getElementById('budget-range').value;
    const selectedExperience = document.getElementById('exp-select').value;
    
    // Собираем все выбранные чекбоксы типов отдыха
    const selectedTypes = Array.from(document.querySelectorAll('input[name="type"]:checked'))
                               .map(cb => cb.value);

    const filtered = routes.filter(route => {
        // Проверка по бюджету (daily_cost из вашего JSON)
        const matchesBudget = route.daily_cost <= maxBudget;
        
        // Проверка по опыту
        const matchesExp = selectedExperience === 'all' || route.experience === selectedExperience;
        
        // Проверка по типу (если ничего не выбрано — показываем все)
        const matchesType = selectedTypes.length === 0 || selectedTypes.includes(route.type);

        return matchesBudget && matchesExp && matchesType;
    });

    displayRoutes(filtered); // Вызываем функцию отрисовки карточек
}

// Слушатель событий на кнопку
document.getElementById('apply-filters').addEventListener('click', () => {
    // Предполагаем, что исходные данные хранятся в переменной allRoutes
    filterRoutes(allRoutes);
});

// Обновление цифры бюджета при движении ползунка
document.getElementById('budget-range').oninput = function() {
    document.getElementById('budget-val').innerHTML = this.value;
};