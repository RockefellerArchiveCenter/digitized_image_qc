document.addEventListener('DOMContentLoaded', function() {

    // Checkbox validation
    const checkboxes = document.querySelectorAll('input[type=checkbox]');
    const checkboxLength = checkboxes.length;
    const firstCheckbox = checkboxLength > 0 ? checkboxes[0] : null;
    approveButton = document.getElementById('approve-button')
    const errorElement = document.getElementById('error-message')

    function init() {
        if (firstCheckbox) {
            checkboxes.forEach(function(el) {
                el.addEventListener('change', checkValidity)
            })
        }
        document.querySelectorAll('.btn--list').forEach(function(element) {
            element.addEventListener('click', checkValidity)
        })

        approveButton && approveButton.addEventListener('click', openModal)
    }

    function isChecked() {
        return Array.prototype.slice.call(checkboxes).some(x => x.checked)
    }

    function checkValidity() {
        const errorMessage = !isChecked() ? 'At least one checkbox must be selected.' : '';
        firstCheckbox.setCustomValidity(errorMessage);
        errorElement.innerHTML = errorMessage ? `<p class="input__error">${errorMessage}</p>` : '';
        return isChecked()
    }

    function openModal() {
        if (checkValidity()) {
            MicroModal.show('modal__approve')
        }
    }

    init();
});