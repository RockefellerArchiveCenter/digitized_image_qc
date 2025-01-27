// Appends rights IDs to form URL query parameters

document.addEventListener('DOMContentLoaded', function() {

    const selectText = 'Select all items'
    const deselectText = 'Deselect all items'

    var button = document.getElementById('select-toggle');
    var checkboxes = document.querySelectorAll('.select-package');

    function toggleSelectAll() {
        console.log(button.ariaPressed)
        if (button.innerHTML == selectText) {
            button.innerHTML = deselectText
            button.ariaLabel = deselectText
            button.ariaPressed = true
            checkboxes.forEach(function(el) {
                    el.checked = true
                }
            )
        } else {
            button.innerHTML = selectText
            button.ariaLabel = selectText
            button.ariaPressed = false
            checkboxes.forEach(function(el) {
                    el.checked = false
                }
            )
        }
    }

    button.addEventListener('click', toggleSelectAll)
});