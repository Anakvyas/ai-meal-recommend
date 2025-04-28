document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('recommendationForm');
    const recommendationsDiv = document.getElementById('recommendations');
    const insightsContent = document.getElementById('insights-content');
    const tabButtons = document.querySelectorAll('.tab-button');

    // Set default date to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('date').value = today;

    // Load insights on page load
    loadInsights();

    // Tab switching
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            loadInsights(button.dataset.tab);
        });
    });

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {
            goal: document.getElementById('goal').value,
            diet_type: document.getElementById('diet_type').value,
            date: document.getElementById('date').value,
            user_id: 'default_user'
        };

        try {
            const response = await fetch('/recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();

            if (data.status === 'success') {
                displayRecommendations(data.recommendations, data.meal_details);
                loadInsights(); // Reload insights after new recommendation
            } else {
                displayError(data.message);
            }
        } catch (error) {
            displayError('An error occurred while fetching recommendations.');
        }
    });

    async function loadInsights(tab = 'history') {
        try {
            const selectedDate = document.getElementById('date').value;
            const response = await fetch(`/user_insights/default_user?date=${selectedDate}`);
            const data = await response.json();

            if (data.status === 'success') {
                switch(tab) {
                    case 'history':
                        displayHistory(data.insights.history);
                        break;
                    case 'predictions':
                        displayPredictions(data.insights.predictions);
                        break;
                    case 'stats':
                        displayStats(data.insights.stats);
                        break;
                }
            } else {
                displayError(data.message);
            }
        } catch (error) {
            displayError('An error occurred while loading insights.');
        }
    }

    function displayHistory(history) {
        let html = '<div class="insight-card">';
        html += '<h3>Your Meal History</h3>';
        
        if (Object.keys(history).length === 0) {
            html += '<p>No meal history available yet.</p>';
        } else {
            for (const [date, meals] of Object.entries(history)) {
                html += `<div class="prediction-card">`;
                html += `<h3>${formatDate(date)}</h3>`;
                html += '<div class="prediction-meals">';
                
                for (const [mealTime, meal] of Object.entries(meals)) {
                    if (meal !== "No valid meal found" && meal !== "Model not loaded") {
                        html += `
                            <div class="prediction-meal">
                                <h4>${capitalizeFirst(mealTime)}</h4>
                                <p>${meal}</p>
                            </div>
                        `;
                    }
                }
                
                html += '</div></div>';
            }
        }
        
        html += '</div>';
        insightsContent.innerHTML = html;
    }

    function displayPredictions(predictions) {
        let html = '<div class="insight-card">';
        html += '<h3>Future Meal Predictions</h3>';
        
        if (Object.keys(predictions).length === 0) {
            html += '<p>No predictions available yet.</p>';
        } else {
            for (const [date, meals] of Object.entries(predictions)) {
                html += `<div class="prediction-card">`;
                html += `<h3>${formatDate(date)}</h3>`;
                html += '<div class="prediction-meals">';
                
                for (const [mealTime, meal] of Object.entries(meals)) {
                    html += `
                        <div class="prediction-meal">
                            <h4>${capitalizeFirst(mealTime)}</h4>
                            <p>${meal.meal}</p>
                            <p>Calories: ${meal.calories}</p>
                            <p>Diet Type: ${capitalizeFirst(meal.diet_type)}</p>
                            <p>Goal: ${capitalizeFirst(meal.goal)}</p>
                        </div>
                    `;
                }
                
                html += '</div></div>';
            }
        }
        
        html += '</div>';
        insightsContent.innerHTML = html;
    }

    function displayStats(stats) {
        let html = '<div class="insight-card">';
        html += '<h3>Your Meal Statistics</h3>';
        
        if (Object.keys(stats).length === 0) {
            html += '<p>No statistics available yet.</p>';
        } else {
            for (const [mealTime, stat] of Object.entries(stats)) {
                html += `
                    <div class="stat-item">
                        <h4>${capitalizeFirst(mealTime)}</h4>
                        <p>Average Calories: ${Math.round(stat.avg_calories)}</p>
                        <p>Total Meals: ${stat.total_meals}</p>
                        <p>Most Common Meals:</p>
                        <ul>
                            ${stat.most_common.map(([meal, count]) => 
                                `<li>${meal} (${count} times)</li>`
                            ).join('')}
                        </ul>
                    </div>
                `;
            }
        }
        
        html += '</div>';
        insightsContent.innerHTML = html;
    }

    function displayRecommendations(recommendations, mealDetails) {
        recommendationsDiv.innerHTML = '<h2>Your Meal Recommendations</h2>';

        const mealTimes = ['breakfast', 'lunch', 'dinner'];
        
        mealTimes.forEach(mealTime => {
            const meal = recommendations[mealTime];
            const details = mealDetails[mealTime];
            
            const mealCard = document.createElement('div');
            mealCard.className = 'meal-card';
            
            let mealHtml = `<h3>${capitalizeFirst(mealTime)}</h3>`;
            
            if (meal === "No valid meal found" || meal === "Model not loaded") {
                mealHtml += `<p class="error-message">${meal}</p>`;
            } else {
                mealHtml += `
                    <div class="meal-details">
                        <p><strong>Meal:</strong> ${meal}</p>
                        ${details ? `
                            <p><strong>Calories:</strong> ${details.total_calories}</p>
                        ` : ''}
                    </div>
                `;
            }
            
            mealCard.innerHTML = mealHtml;
            recommendationsDiv.appendChild(mealCard);
        });
    }

    function displayError(message) {
        recommendationsDiv.innerHTML = `
            <div class="error-message">
                ${message}
            </div>
        `;
    }

    function capitalizeFirst(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }

    function formatDate(dateString) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        return new Date(dateString).toLocaleDateString(undefined, options);
    }
}); 