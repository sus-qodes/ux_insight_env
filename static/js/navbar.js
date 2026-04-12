// Navbar injection script - detects current page and highlights active link
document.addEventListener('DOMContentLoaded', function() {
  const navbarHTML = `
    <nav class="navbar">
      <div class="navbar-container">
        <div class="navbar-brand">
          <a href="/" class="brand-link">UX Insight Analyst</a>
        </div>
        <button class="navbar-toggle" aria-label="Toggle navigation">
          <span class="hamburger"></span>
        </button>
        <ul class="navbar-menu">
          <li><a href="/" class="nav-link">Home</a></li>
          <li><a href="/overview" class="nav-link">Overview</a></li>
          <li><a href="/documentation" class="nav-link">Documentation</a></li>
          <li><a href="/web" class="nav-link">OpenEnv</a></li>
          <li><a href="/custom-playground" class="nav-link">Playground</a></li>
          <li><a href="/config" class="nav-link">Template</a></li>
        </ul>
      </div>
    </nav>
  `;

  // Insert navbar at the beginning of body
  document.body.insertAdjacentHTML('afterbegin', navbarHTML);

  // Highlight active link
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-link');

  navLinks.forEach(link => {
    const linkHref = link.getAttribute('href');
    if (linkHref === currentPath || (currentPath === '/' && linkHref === '/')) {
      link.classList.add('active');
    }
  });

  // Mobile menu toggle
  const toggle = document.querySelector('.navbar-toggle');
  const menu = document.querySelector('.navbar-menu');

  if (toggle) {
    toggle.addEventListener('click', function() {
      menu.classList.toggle('active');
    });
  }

  // Close menu when link clicked
  navLinks.forEach(link => {
    link.addEventListener('click', function() {
      menu.classList.remove('active');
    });
  });
});
