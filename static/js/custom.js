// Vehicle Tax Calculator - jQuery Version

$(document).ready(function() {
    initCalculator();
});

function initCalculator() {
    // Category change - show/hide CC field
    $('#category').change(function() {
        const hasCc = $(this).find(':selected').data('has-cc');
        const ccRow = $('#ccRow');
        const ccInput = $('input[name="cc_power"]');

        if (hasCc) {
            ccRow.slideDown();
            ccInput.prop('required', true);
        } else {
            ccRow.slideUp();
            ccInput.prop('required', false).val('');
        }
    });

    // Date formatting with Nepali calendar validation
    $('.date-input').on('input', function() {
        let value = $(this).val().replace(/[^\d]/g, '');
        if (value.length >= 4) value = value.substring(0,4) + '-' + value.substring(4);
        if (value.length >= 7) value = value.substring(0,7) + '-' + value.substring(7,9);
        $(this).val(value);
    });

    // Date validation on blur
    $('.date-input').on('blur', function() {
        const value = $(this).val();
        if (value && !isValidNepaliDate(value)) {
            $(this).addClass('is-invalid');
            showAlert('warning', 'Please enter a valid Nepali date (2070-2090)');
        } else {
            $(this).removeClass('is-invalid');
        }
    });

    // Form submission
    $('#taxForm').submit(function(e) {
        e.preventDefault();

        if (validateForm()) {
            submitForm();
        } else {
            showAlert('danger', 'Please fill all required fields correctly.');
        }
    });

    // Add input validation helpers
    $('input[name="cc_power"]').on('input', function() {
        const value = parseFloat($(this).val());
        if (value <= 0) {
            $(this).addClass('is-invalid');
        } else {
            $(this).removeClass('is-invalid');
        }
    });
}

function validateForm() {
    let isValid = true;

    // Check required fields
    $('#taxForm [required]').each(function() {
        if (!$(this).val().trim()) {
            $(this).addClass('is-invalid');
            isValid = false;
        } else {
            $(this).removeClass('is-invalid');
        }
    });

    // Date validation
    $('.date-input').each(function() {
        const value = $(this).val();
        if (value && !isValidNepaliDate(value)) {
            $(this).addClass('is-invalid');
            isValid = false;
        }
    });

    // CC/Power validation for categories that require it
    const category = $('#category').find(':selected');
    const hasCc = category.data('has-cc');
    const ccInput = $('input[name="cc_power"]');

    if (hasCc && (!ccInput.val() || parseFloat(ccInput.val()) <= 0)) {
        ccInput.addClass('is-invalid');
        isValid = false;
    }

    // Date range validation
    const lastPaid = $('input[name="last_paid_date"]').val();
    const nextPayment = $('input[name="next_payment_date"]').val();

    if (lastPaid && nextPayment && lastPaid >= nextPayment) {
        $('input[name="next_payment_date"]').addClass('is-invalid');
        showAlert('danger', 'Next payment date must be after last paid date.');
        isValid = false;
    }

    return isValid;
}

function isValidNepaliDate(dateStr) {
    const pattern = /^\d{4}-\d{2}-\d{2}$/;
    if (!pattern.test(dateStr)) return false;

    const [year, month, day] = dateStr.split('-').map(Number);
    return year >= 2070 && year <= 2090 && month >= 1 && month <= 12 && day >= 1 && day <= 32;
}

function submitForm() {
    const btn = $('.btn-calculate');
    const loading = $('#loading');

    // Show loading
    btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-2"></span>Calculating...');
    loading.show();

    // Get CSRF token
    const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();

    // Submit
    $.ajax({
        url: window.calculateUrl,
        method: 'POST',
        data: $('#taxForm').serialize(),
        headers: {
            'X-CSRFToken': csrfToken
        },
        success: function(response) {
            hideLoading();

            if (response.success) {
                displayResults(response.result);
                showAlert('success', 'Tax calculation completed successfully!');
            } else {
                showAlert('danger', response.error || 'Calculation failed.');
                if (response.errors) {
                    console.log('Form errors:', response.errors);
                }
            }
        },
        error: function(xhr, status, error) {
            hideLoading();
            let errorMessage = 'Network error. Please try again.';

            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMessage = xhr.responseJSON.error;
            }

            showAlert('danger', errorMessage);
            console.error('Ajax error:', error);
        }
    });
}

function hideLoading() {
    $('.btn-calculate').prop('disabled', false).html('<i class="fas fa-calculator"></i> Calculate Tax');
    $('#loading').hide();
}

function displayResults(result) {
    let html = `
        <h3><i class="fas fa-receipt"></i> Tax Calculation Results</h3>
        
        <!-- Vehicle Info -->
        <div class="calculation-card">
            <h5><i class="fas fa-info-circle"></i> Vehicle Information</h5>
            <div class="row">
                <div class="col-md-4"><strong>Type:</strong> ${result.vehicle_info.reg_type}</div>
                <div class="col-md-4"><strong>Category:</strong> ${result.vehicle_info.category}</div>
                <div class="col-md-4"><strong>CC/Power:</strong> ${result.vehicle_info.cc_power ? result.vehicle_info.cc_power + ' CC/KW' : 'N/A'}</div>
            </div>
            ${result.vehicle_info.cc_range ? `<div class="mt-2"><strong>CC Range:</strong> ${result.vehicle_info.cc_range}</div>` : ''}
        </div>
    `;

    // Fiscal years
    if (result.fiscal_years && result.fiscal_years.length > 0) {
        result.fiscal_years.forEach(function(year) {
            html += `
                <div class="calculation-card">
                    <h5><i class="fas fa-calendar"></i> ${year.fiscal_year}</h5>
                    <div class="row text-center">
                        <div class="col-md-3">
                            <strong>Vehicle Tax</strong><br>
                            <span class="fs-5 text-success">Rs. ${formatMoney(year.tax_amount || 0)}</span>
                        </div>
                        <div class="col-md-3">
                            <strong>Renewal Fee</strong><br>
                            <span class="fs-5 text-primary">Rs. ${formatMoney(year.renewal_fee || 0)}</span>
                        </div>
                        <div class="col-md-3">
                            <strong>Income Tax</strong><br>
                            <span class="fs-5 text-info">Rs. ${formatMoney(year.income_tax || 0)}</span>
                        </div>
                        <div class="col-md-3">
                            <strong>Penalty</strong><br>
                            <span class="fs-5 text-danger">Rs. ${formatMoney(year.penalty || 0)}</span>
                        </div>
                    </div>
                    ${year.case_note ? `<div class="case-note mt-2"><i class="fas fa-info-circle"></i> ${year.case_note}</div>` : ''}
                </div>
            `;
        });
    }

    // Total
    html += `
        <div class="calculation-card total-card">
            <h4><i class="fas fa-calculator"></i> Total Summary</h4>
            <div class="row text-center mb-3">
                <div class="col-md-3">
                    <strong>Total Vehicle Tax</strong><br>
                    <h5>Rs. ${formatMoney(result.total_tax || 0)}</h5>
                </div>
                <div class="col-md-3">
                    <strong>Total Renewal Fee</strong><br>
                    <h5>Rs. ${formatMoney(result.total_renewal_fee || 0)}</h5>
                </div>
                <div class="col-md-3">
                    <strong>Total Income Tax</strong><br>
                    <h5>Rs. ${formatMoney(result.total_income_tax || 0)}</h5>
                </div>
                <div class="col-md-3">
                    <strong>Total Penalty</strong><br>
                    <h5>Rs. ${formatMoney(result.total_penalty || 0)}</h5>
                </div>
            </div>
            <hr style="border-color: rgba(255,255,255,0.3);">
            <div class="text-center">
                <h2><strong>Grand Total: Rs. ${formatMoney(result.grand_total || 0)}</strong></h2>
            </div>
            <div class="text-center mt-3">
                <button class="btn btn-light" onclick="printResults()">
                    <i class="fas fa-print"></i> Print Results
                </button>
                <button class="btn btn-light ms-2" onclick="resetForm()">
                    <i class="fas fa-calculator"></i> New Calculation
                </button>
            </div>
        </div>
    `;

    $('#results').html(html).show();

    // Smooth scroll to results
    $('html, body').animate({
        scrollTop: $('#results').offset().top - 50
    }, 500);
}

function showAlert(type, message) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : 'exclamation-circle'}"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    $('#alerts').html(alertHtml);

    if (type === 'success') {
        setTimeout(() => $('.alert').alert('close'), 5000);
    }
}

function formatMoney(amount) {
    return parseFloat(amount || 0).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function resetForm() {
    $('#taxForm')[0].reset();
    $('#ccRow').hide();
    $('#results').hide();
    $('#alerts').empty();
    $('.is-invalid').removeClass('is-invalid');

    // Smooth scroll to top
    $('html, body').animate({
        scrollTop: 0
    }, 500);
}

function printResults() {
    const content = $('#results').html();
    const printWindow = window.open('', '_blank');

    printWindow.document.write(`
        <html>
        <head>
            <title>Vehicle Tax Calculation Results</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body { padding: 20px; font-family: Arial, sans-serif; }
                .calculation-card { 
                    border: 1px solid #ddd; 
                    padding: 15px; 
                    margin-bottom: 15px; 
                    border-radius: 8px;
                }
                .total-card { 
                    background-color: #d4edda; 
                    border-color: #c3e6cb;
                }
                .case-note { 
                    background-color: #f8f9fa; 
                    padding: 8px; 
                    border-radius: 4px; 
                    font-size: 0.9em; 
                }
                @media print { 
                    .btn { display: none !important; } 
                    .no-print { display: none !important; }
                }
            </style>
        </head>
        <body>
            <h2>Vehicle Tax Calculation Results</h2>
            <p><strong>Date:</strong> ${new Date().toLocaleDateString()}</p>
            <p><strong>Generated by:</strong> Gandaki Province Vehicle Tax Calculator</p>
            <hr>
            ${content}
        </body>
        </html>
    `);

    printWindow.document.close();
    setTimeout(() => {
        printWindow.print();
        printWindow.close();
    }, 250);
}

// Keyboard shortcuts
$(document).keydown(function(e) {
    if (e.ctrlKey && e.which === 13) { // Ctrl+Enter
        e.preventDefault();
        $('#taxForm').submit();
    }
    if (e.which === 27) { // Escape
        resetForm();
    }
});

// Add helpful tooltips for better UX
$(document).ready(function() {
    // Initialize tooltips if Bootstrap tooltip is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});