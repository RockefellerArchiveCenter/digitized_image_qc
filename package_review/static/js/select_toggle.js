// Appends rights IDs to form URL query parameters

function toggleSelectAll(button, checkboxes, e) {
        const selectText = 'Select all items'
        const deselectText = 'Deselect all items'

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

$(document).ready(function() {

    // Wait for datatable to be rendered
    $('#package-list').on('draw.dt', function(e) {
        var checkboxes = document.querySelectorAll('.select-package');

        var button = document.getElementById('select-toggle');
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);

        var button = document.getElementById('select-toggle');
        button.addEventListener('click', function(e) {toggleSelectAll(button, checkboxes, e)})
    })
});