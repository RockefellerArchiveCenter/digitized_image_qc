// Mobile navigation toggle

document.getElementById('nav-toggle').addEventListener('click', function() {
  const expandedCurrent = this.getAttribute('aria-expanded');

  // Sets classes and attributes on the nav-toggle
  this.classList.toggle('active');
  this.classList.toggle('closed');
  this.setAttribute('aria-expanded', expandedCurrent === 'true' ? 'false' : 'true');

  // Sets classes and attributes on the nav-toggle-menu
  const menu = document.getElementById('nav-toggle-menu');
  menu.classList.toggle('active');
  menu.classList.toggle('closed');
});

// Closes the menu on Esc and returns focus to the nav-toggle
document.addEventListener('keydown', function(event) {
  const toggle = document.getElementById('nav-toggle');
  if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
    toggle.click();
    toggle.focus();
  }
});
