// Vehicle Tax Calculator JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeCalculator();
});

function initializeCalculator() {
    // Show/hide CC range input based on category selection
    const categorySelect = document.getElementById('category');
    const ccRangeInput = document.querySelector('.cc-range-input');
    const ccPowerInput = document.getElementById('cc_power');

    categorySelect.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        const hasCCRange = selectedOption.dataset.hasCc === 'True';

        if (hasCCRange) {
            ccRangeInput.style.display = 'block';
            ccPowerInput.required = true;
        } else {
            ccRangeInput.style.display = 'none';
            ccPowerInput.required = false;
            ccPowerInput.value = '';
        }
    });

    // Form submission
    const form = document.getElementById('taxCalculatorForm');
    form.addEventListener('submit', handleFormSubmission);

    // Auto-format date inputs
    setupDateFormatting();

    // Add date validation
    setupDateValidation();

    // Initialize Bootstrap tooltips
    initializeTooltips();
}

function handleFormSubmission(e) {
    e.preventDefault();

    const loadingDiv = document.querySelector('.loading');
    const errorDiv = document.getElementById('errorMessage');
    const successDiv = document.getElementById('successMessage');
    const resultsSection = document.getElementById('resultsSection');

    // Show loading
    showLoading();
    hideMessages();

    // Prepare form data
    const formData = new FormData(e.target);

    // Get CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Make AJAX request
    fetch(getCalculateUrl(), {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        hideLoading();

        if (data.success) {
            displayResults(data.result);
            showResults();
            showSuccessMessage('Tax calculation completed successfully!');
        } else {
            showErrorMessage(data.error || 'An error occurred while calculating tax.');
        }
    })
    .catch(error => {
        hideLoading();
        showErrorMessage('Network error. Please check your connection and try again.');
        console.error('Calculation Error:', error);
    });
}

function displayResults(result) {
    const resultsContainer = document.getElementById('calculationResults');

    let html = buildVehicleInfoCard(result.vehicle_info);

    // Case information and fiscal year details
    if (result.calculation_details) {
        html += buildCaseInfoCard(result.calculation_details);
    }

    // Fiscal year details
    html += buildFiscalYearCards(result.fiscal_years);

    // Total summary
    html += buildTotalSummaryCard(result);

    // Calculation methodology info
    html += buildCalculationRulesCard();

    resultsContainer.innerHTML = html;

    // Add animation classes
    setTimeout(() => {
        const cards = resultsContainer.querySelectorAll('.calculation-card');
        cards.forEach((card, index) => {
            setTimeout(() => {
                card.classList.add('fadeIn');
            }, index * 100);
        });
    }, 100);
}

function buildVehicleInfoCard(vehicleInfo) {
    return `
        <div class="calculation-card">
            <h5><i class="fas fa-info-circle"></i> Vehicle Information</h5>
            <div class="row">
                <div class="col-md-4">
                    <strong>Registration Type:</strong><br>
                    <span class="text-primary">${vehicleInfo.reg_type}</span>
                </div>
                <div class="col-md-4">
                    <strong>Category:</strong><br>
                    <span class="text-info">${vehicleInfo.category}</span>
                </div>
                <div class="col-md-4">
                    <strong>CC/Power Range:</strong><br>
                    <span class="text-success">${vehicleInfo.cc_range}</span>
                </div>
            </div>
        </div>
    `;
}

function buildCaseInfoCard(calculationDetails) {
    return `
        <div class="calculation-card case-info-card">
            <h5><i class="fas fa-sitemap"></i> Calculation Method</h5>
            <div class="row">
                <div class="col-md-4">
                    <strong>Last Paid FY:</strong><br>
                    ${calculationDetails.last_paid_fy || 'N/A'}
                </div>
                <div class="col-md-4">
                    <strong>Next Payment FY:</strong><br>
                    ${calculationDetails.next_payment_fy || 'N/A'}
                </div>
                <div class="col-md-4">
                    <strong>Current FY:</strong><br>
                    ${calculationDetails.current_fy || 'N/A'}
                </div>
            </div>
            <div class="mt-3">
                <span class="case-badge">${calculationDetails.case_applied || 'N/A'}</span>
            </div>
        </div>
    `;
}

function buildFiscalYearCards(fiscalYears) {
    return fiscalYears.map((year, index) => {
        const badges = [];
        if (year.is_renewal_only) {
            badges.push('<span class="renewal-badge">Renewal Only</span>');
        }
        if (year.penalty > 0) {
            badges.push('<span class="penalty-badge">Penalty Applied</span>');
        }

        const penaltyDetails = year.penalty_details && year.penalty_details.length > 0 ? `
            <div class="mt-3">
                <h6><i class="fas fa-exclamation-triangle"></i> Penalty Breakdown:</h6>
                ${year.penalty_details.map(detail => `
                    <div class="penalty-detail mb-2">
                        <span class="penalty-badge">${detail.type}</span>
                        <small class="ms-2">
                            ${detail.rate} → Rs. ${formatCurrency(detail.amount)}
                        </small>
                    </div>
                `).join('')}
            </div>
        ` : '';

        return `
            <div class="calculation-card">
                <h5>
                    <i class="fas fa-calendar"></i> ${year.fiscal_year}
                    ${badges.join(' ')}
                </h5>
                
                ${year.case_note ? `<div class="case-note"><i class="fas fa-info-circle"></i> ${year.case_note}</div>` : ''}

                <div class="fiscal-year-details">
                    <div class="row">
                        <div class="col-md-3">
                            <strong>Vehicle Tax:</strong><br>
                            <span class="text-success fs-5">Rs. ${formatCurrency(year.tax_amount)}</span>
                        </div>
                        <div class="col-md-3">
                            <strong>Renewal Fee:</strong><br>
                            <span class="text-primary fs-5">Rs. ${formatCurrency(year.renewal_fee)}</span>
                        </div>
                        <div class="col-md-3">
                            <strong>Income Tax:</strong><br>
                            <span class="text-info fs-5">Rs. ${formatCurrency(year.income_tax)}</span>
                        </div>
                        <div class="col-md-3">
                            <strong>Penalty:</strong><br>
                            <span class="text-danger fs-5">Rs. ${formatCurrency(year.penalty)}</span>
                        </div>
                    </div>
                    ${penaltyDetails}
                </div>
            </div>
        `;
    }).join('');
}

function buildTotalSummaryCard(result) {
    return `
        <div class="calculation-card total-card">
            <h4><i class="fas fa-calculator"></i> Total Summary</h4>
            <div class="row">
                <div class="col-md-3 text-center">
                    <strong>Total Vehicle Tax</strong><br>
                    <h5 class="mt-2">Rs. ${formatCurrency(result.total_tax)}</h5>
                </div>
                <div class="col-md-3 text-center">
                    <strong>Total Renewal Fee</strong><br>
                    <h5 class="mt-2">Rs. ${formatCurrency(result.total_renewal_fee)}</h5>
                </div>
                <div class="col-md-3 text-center">
                    <strong>Total Income Tax</strong><br>
                    <h5 class="mt-2">Rs. ${formatCurrency(result.total_income_tax)}</h5>
                </div>
                <div class="col-md-3 text-center">
                    <strong>Total Penalty</strong><br>
                    <h5 class="mt-2">Rs. ${formatCurrency(result.total_penalty)}</h5>
                </div>
            </div>
            <hr style="border-color: rgba(255,255,255,0.3);">
            <div class="text-center">
                <h2><strong><i class="fas fa-coins"></i> Grand Total: Rs. ${formatCurrency(result.grand_total)}</strong></h2>
            </div>
            <div class="text-center mt-3">
                <button class="btn btn-light" onclick="printResults()">
                    <i class="fas fa-print"></i> Print Results
                </button>
                <button class="btn btn-light ms-2" onclick="downloadResults()">
                    <i class="fas fa-download"></i> Download PDF
                </button>
            </div>
        </div>
    `;
}

function buildCalculationRulesCard() {
    return `
        <div class="calculation-card rules-card">
            <h6><i class="fas fa-lightbulb"></i> Calculation Rules Applied</h6>
            <div class="row">
                <div class="col-md-6">
                    <h6>CASE I - Same Fiscal Year:</h6>
                    <ul class="small">
                        <li>Same FY for all dates: Only renewal fee</li>
                        <li>Within 90 days: No penalty</li>
                        <li>Beyond 90 days: Double renewal fee</li>
                    </ul>
                </div>
                <div class="col-md-6">
                    <h6>CASE II - Different Fiscal Years:</h6>
                    <ul class="small">
                        <li>After 1 year: Triple renewal fee</li>
                        <li>Vehicle tax penalty: 5% (30 days), 10% (75 days), 20% (same FY)</li>
                        <li>Multiple years: Full tax + 20% penalty per year</li>
                    </ul>
                </div>
            </div>
        </div>
    `;
}

function setupDateFormatting() {
    ['last_paid_date', 'next_payment_date'].forEach(id => {
        const input = document.getElementById(id);
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^\d]/g, '');
            if (value.length >= 4) {
                value = value.substring(0,4) + '-' + value.substring(4);
            }
            if (value.length >= 7) {
                value = value.substring(0,7) + '-' + value.substring(7,9);
            }
            e.target.value = value;
        });
    });
}

function setupDateValidation() {
    ['last_paid_date', 'next_payment_date'].forEach(id => {
        const input = document.getElementById(id);
        input.addEventListener('blur', function(e) {
            const dateValue = e.target.value;
            if (dateValue && !isValidNepaliDate(dateValue)) {
                e.target.setCustomValidity('Please enter a valid Nepali date (YYYY-MM-DD)');
                e.target.classList.add('is-invalid');
            } else {
                e.target.setCustomValidity('');
                e.target.classList.remove('is-invalid');
            }
        });
    });
}

function isValidNepaliDate(dateString) {
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(dateString)) return false;

    const [year, month, day] = dateString.split('-').map(Number);

    // Basic validation for Nepali calendar
    if (year < 2000 || year > 2100) return false;
    if (month < 1 || month > 12) return false;
    if (day < 1 || day > 32) return false;

    return true;
}

function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Utility functions
function formatCurrency(amount) {
    return parseFloat(amount).toLocaleString('en-IN', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
}

function showLoading() {
    document.querySelector('.loading').style.display = 'block';
}

function hideLoading() {
    document.querySelector('.loading').style.display = 'none';
}

function showResults() {
    const resultsSection = document.getElementById('resultsSection');
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function hideMessages() {
    document.getElementById('errorMessage').style.display = 'none';
    document.getElementById('successMessage').style.display = 'none';
    document.getElementById('warningMessage').style.display = 'none';
}

function showErrorMessage(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    errorDiv.scrollIntoView({ behavior: 'smooth' });
}

function showSuccessMessage(message) {
    const successDiv = document.getElementById('successMessage');
    successDiv.textContent = message;
    successDiv.style.display = 'block';
}

function showWarningMessage(message) {
    const warningDiv = document.getElementById('warningMessage');
    warningDiv.textContent = message;
    warningDiv.style.display = 'block';
}

function getCalculateUrl() {
    // This should be dynamically generated or passed from the template
    return '/calculate/';
}

function printResults() {
    window.print();
}

function downloadResults() {
    // Placeholder for PDF download functionality
    showWarningMessage('PDF download feature will be implemented in a future update.');
}

// Reset form function
function resetForm() {
    document.getElementById('taxCalculatorForm').reset();
    document.getElementById('resultsSection').style.display = 'none';
    document.querySelector('.cc-range-input').style.display = 'none';
    hideMessages();
}

// Export functions for global access
window.CalculatorApp = {
    resetForm: resetForm,
    printResults: printResults,
    downloadResults: downloadResults,
    showErrorMessage: showErrorMessage,
    showSuccessMessage: showSuccessMessage,
    showWarningMessage: showWarningMessage,
    formatCurrency: formatCurrency,
    isValidNepaliDate: isValidNepaliDate
};

// Additional utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Auto-save form data to localStorage (if needed)
function saveFormData() {
    const formData = new FormData(document.getElementById('taxCalculatorForm'));
    const data = {};
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    localStorage.setItem('vehicleTaxFormData', JSON.stringify(data));
}

function loadFormData() {
    const savedData = localStorage.getItem('vehicleTaxFormData');
    if (savedData) {
        const data = JSON.parse(savedData);
        Object.keys(data).forEach(key => {
            const input = document.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = data[key];
                // Trigger change event for selects
                if (input.tagName === 'SELECT') {
                    input.dispatchEvent(new Event('change'));
                }
            }
        });
    }
}

// Clear saved form data
function clearSavedData() {
    localStorage.removeItem('vehicleTaxFormData');
}

// Form validation helpers
function validateForm() {
    const form = document.getElementById('taxCalculatorForm');
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });

    // Validate date formats
    const lastPaidDate = document.getElementById('last_paid_date').value;
    const nextPaymentDate = document.getElementById('next_payment_date').value;

    if (lastPaidDate && !isValidNepaliDate(lastPaidDate)) {
        document.getElementById('last_paid_date').classList.add('is-invalid');
        isValid = false;
    }

    if (nextPaymentDate && !isValidNepaliDate(nextPaymentDate)) {
        document.getElementById('next_payment_date').classList.add('is-invalid');
        isValid = false;
    }

    // Validate date logic (next payment should be after last paid)
    if (lastPaidDate && nextPaymentDate && isValidNepaliDate(lastPaidDate) && isValidNepaliDate(nextPaymentDate)) {
        if (compareDates(lastPaidDate, nextPaymentDate) >= 0) {
            showWarningMessage('Next payment date should be after last paid date.');
            isValid = false;
        }
    }

    return isValid;
}

function compareDates(date1, date2) {
    // Simple date comparison for YYYY-MM-DD format
    return date1.localeCompare(date2);
}

// Real-time form validation
function setupRealTimeValidation() {
    const form = document.getElementById('taxCalculatorForm');
    const inputs = form.querySelectorAll('input, select');

    inputs.forEach(input => {
        input.addEventListener('blur', debounce(() => {
            validateField(input);
        }, 300));

        input.addEventListener('input', debounce(() => {
            if (input.classList.contains('is-invalid')) {
                validateField(input);
            }
        }, 500));
    });
}

function validateField(field) {
    if (field.hasAttribute('required') && !field.value.trim()) {
        field.classList.add('is-invalid');
        return false;
    }

    if (field.type === 'text' && (field.id === 'last_paid_date' || field.id === 'next_payment_date')) {
        if (field.value && !isValidNepaliDate(field.value)) {
            field.classList.add('is-invalid');
            return false;
        }
    }

    field.classList.remove('is-invalid');
    return true;
}

// Enhanced form submission with validation
function enhancedFormSubmission(e) {
    e.preventDefault();

    if (!validateForm()) {
        showErrorMessage('Please fill in all required fields correctly.');
        return;
    }

    // Save form data before submission
    saveFormData();

    // Proceed with original submission
    handleFormSubmission(e);
}

// Initialize enhanced features
function initializeEnhancedFeatures() {
    setupRealTimeValidation();

    // Load saved form data on page load
    loadFormData();

    // Replace form submission handler
    const form = document.getElementById('taxCalculatorForm');
    form.removeEventListener('submit', handleFormSubmission);
    form.addEventListener('submit', enhancedFormSubmission);

    // Add reset button functionality
    const resetButton = document.createElement('button');
    resetButton.type = 'button';
    resetButton.className = 'btn btn-outline-secondary ms-2';
    resetButton.innerHTML = '<i class="fas fa-undo"></i> Reset';
    resetButton.onclick = () => {
        resetForm();
        clearSavedData();
    };

    const calculateButton = document.querySelector('.btn-calculate');
    if (calculateButton) {
        calculateButton.parentNode.appendChild(resetButton);
    }
}

// Update the initialization to include enhanced features
document.addEventListener('DOMContentLoaded', function() {
    initializeCalculator();
    initializeEnhancedFeatures();
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl + Enter to submit form
    if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        const form = document.getElementById('taxCalculatorForm');
        form.dispatchEvent(new Event('submit'));
    }

    // Escape to reset form
    if (e.key === 'Escape') {
        resetForm();
    }
});

// Add to window object for global access
window.CalculatorApp.validateForm = validateForm;
window.CalculatorApp.saveFormData = saveFormData;
window.CalculatorApp.loadFormData = loadFormData;
window.CalculatorApp.clearSavedData = clearSavedData;