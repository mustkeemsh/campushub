/**
 * CollegeHub - Unified Authentication, Session & Auth Popup Modal Manager
 * Automatically displays Login & Sign Up popup on website visit for unauthenticated users,
 * captures info from forms, and keeps user session synchronized everywhere.
 */
const CollegeHubAuth = (function () {
  'use strict';

  const USER_KEY = 'collegehub_user';
  const LOGGED_IN_KEY = 'collegehub_logged_in';
  const DISMISSED_KEY = 'collegehub_auth_dismissed';

  const DEFAULT_USER = null;

  function getUser() {
    try {
      const stored = localStorage.getItem(USER_KEY);
      if (stored) {
        if (stored.includes('Jordan Miller') || stored.includes('jordan.miller@example.com') || stored.includes('usr-default')) {
          localStorage.removeItem(USER_KEY);
          localStorage.removeItem(LOGGED_IN_KEY);
          return null;
        }
        return JSON.parse(stored);
      }
    } catch (e) {
      console.warn('Error reading user session:', e);
    }
    return null;
  }

  function isLoggedIn() {
    return localStorage.getItem(LOGGED_IN_KEY) === 'true';
  }

  function setUser(userData) {
    if (userData) {
      localStorage.setItem(USER_KEY, JSON.stringify(userData));
      localStorage.setItem(LOGGED_IN_KEY, 'true');
    } else {
      localStorage.removeItem(USER_KEY);
      localStorage.removeItem(LOGGED_IN_KEY);
    }
    updateDOM();
  }

  function logout() {
    fetch('/api/auth/logout', { method: 'POST' })
      .finally(() => {
        setUser(null);
        sessionStorage.removeItem(DISMISSED_KEY);
        window.location.href = '/login';
      });
  }

  /**
   * Submit credentials from Login form: takes info from login page
   */
  async function handleLoginSubmit(event, roleKey) {
    if (event) event.preventDefault();

    const identifierInput = document.getElementById('auth-identifier') || document.getElementById('modal-login-identifier');
    const passwordInput = document.getElementById('auth-password') || document.getElementById('modal-login-password');
    const nameInput = document.getElementById('auth-fullname') || document.getElementById('modal-login-fullname');
    const rememberInput = document.getElementById('remember-me') || document.getElementById('modal-remember-me');
    const submitBtn = document.getElementById('primary-submit-btn') || document.getElementById('modal-login-submit-btn');
    const alertBox = document.getElementById('auth-alert-box') || document.getElementById('modal-auth-alert');

    const identifier = (identifierInput ? identifierInput.value : '').trim();
    const password = (passwordInput ? passwordInput.value : '').trim();
    const fullName = (nameInput ? nameInput.value : '').trim();
    const rememberMe = rememberInput ? rememberInput.checked : true;
    const role = roleKey || (window.activeRole || 'student');

    if (alertBox) {
      alertBox.classList.add('hidden');
      alertBox.innerHTML = '';
    }

    if (!identifier) {
      showAlert('Please enter your Email address, Username, or Applicant ID.', 'error', alertBox);
      if (identifierInput) identifierInput.focus();
      return;
    }

    if (!password) {
      showAlert('Please enter your account password.', 'error', alertBox);
      if (passwordInput) passwordInput.focus();
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.dataset.originalHtml = submitBtn.innerHTML;
      submitBtn.innerHTML = `
        <span class="material-symbols-outlined text-base animate-spin">progress_activity</span>
        <span>Authenticating session...</span>
      `;
    }

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          identifier: identifier,
          password: password,
          role: role,
          full_name: fullName,
          remember_me: rememberMe
        })
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        setUser(data.user);
        showAlert(data.message || 'Login successful! Redirecting...', 'success', alertBox);

        if (submitBtn) {
          submitBtn.innerHTML = `
            <span class="material-symbols-outlined text-base text-secondary-container">check_circle</span>
            <span>Success! Redirecting...</span>
          `;
        }

        setTimeout(() => {
          closeAuthModal();
          window.location.href = data.redirect_url || '/profile';
        }, 500);
      } else {
        showAlert(data.message || 'Invalid credentials. Please verify your login details.', 'error', alertBox);
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = submitBtn.dataset.originalHtml || '<span>Log In</span>';
        }
      }
    } catch (err) {
      console.error('Login error:', err);
      showAlert('Unable to reach authentication service. Please check your connection.', 'error', alertBox);
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = submitBtn.dataset.originalHtml || '<span>Log In</span>';
      }
    }
  }

  /**
   * Submit registration from Sign Up form: takes info from signup page
   */
  async function handleRegisterSubmit(event, roleKey) {
    if (event) event.preventDefault();

    const nameInput = document.getElementById('signup-fullname') || document.getElementById('modal-signup-fullname');
    const emailInput = document.getElementById('signup-email') || document.getElementById('modal-signup-email');
    const passInput = document.getElementById('signup-password') || document.getElementById('modal-signup-password');
    const programInput = document.getElementById('signup-program') || document.getElementById('modal-signup-program');
    const submitBtn = document.getElementById('signup-submit-btn') || document.getElementById('modal-signup-submit-btn');
    const alertBox = document.getElementById('auth-alert-box') || document.getElementById('modal-auth-alert');

    const fullName = (nameInput ? nameInput.value : '').trim();
    const email = (emailInput ? emailInput.value : '').trim();
    const password = (passInput ? passInput.value : '').trim();
    const program = programInput ? programInput.value : 'B.Tech Engineering';
    const role = roleKey || 'student';

    if (alertBox) {
      alertBox.classList.add('hidden');
      alertBox.innerHTML = '';
    }

    if (!fullName) {
      showAlert('Please enter your Full Name.', 'error', alertBox);
      if (nameInput) nameInput.focus();
      return;
    }

    if (!email || !email.includes('@')) {
      showAlert('Please enter a valid Email address.', 'error', alertBox);
      if (emailInput) emailInput.focus();
      return;
    }

    if (!password || password.length < 6) {
      showAlert('Password must be at least 6 characters.', 'error', alertBox);
      if (passInput) passInput.focus();
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.dataset.originalHtml = submitBtn.innerHTML;
      submitBtn.innerHTML = `
        <span class="material-symbols-outlined text-base animate-spin">progress_activity</span>
        <span>Creating your profile...</span>
      `;
    }

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: fullName,
          email: email,
          password: password,
          role: role,
          program: program
        })
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        setUser(data.user);
        showAlert(data.message || 'Account created! Redirecting to Student Hub...', 'success', alertBox);

        if (submitBtn) {
          submitBtn.innerHTML = `
            <span class="material-symbols-outlined text-base text-secondary-container">check_circle</span>
            <span>Welcome! Redirecting...</span>
          `;
        }

        setTimeout(() => {
          closeAuthModal();
          window.location.href = data.redirect_url || '/profile';
        }, 500);
      } else {
        showAlert(data.message || 'Registration failed. Please check your details.', 'error', alertBox);
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = submitBtn.dataset.originalHtml || '<span>Create Account</span>';
        }
      }
    } catch (err) {
      console.error('Registration error:', err);
      showAlert('Unable to connect to server. Please try again.', 'error', alertBox);
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = submitBtn.dataset.originalHtml || '<span>Create Account</span>';
      }
    }
  }

  function showAlert(msg, type, container) {
    const box = container || document.getElementById('auth-alert-box') || document.getElementById('modal-auth-alert');
    if (!box) {
      alert(msg);
      return;
    }

    box.classList.remove('hidden', 'bg-error-container', 'text-on-error-container', 'border-error/20', 'bg-secondary-container', 'text-on-secondary-container', 'border-secondary/20');

    if (type === 'error') {
      box.className = 'p-3 rounded-xl bg-error-container text-on-error-container text-xs font-semibold border border-error/20 flex items-center gap-2 mb-4';
      box.innerHTML = `<span class="material-symbols-outlined text-base shrink-0">error</span><span>${msg}</span>`;
    } else {
      box.className = 'p-3 rounded-xl bg-secondary-container text-on-secondary-container text-xs font-semibold border border-secondary/20 flex items-center gap-2 mb-4';
      box.innerHTML = `<span class="material-symbols-outlined text-base shrink-0">check_circle</span><span>${msg}</span>`;
    }
  }

  /* ==========================================================================
     POPUP MODAL COMPONENT (Auto-pops up when visiting website unauthenticated)
     ========================================================================== */

  let currentModalTab = 'login';
  let modalActiveRole = 'student';

  function injectAuthModal() {
    if (document.getElementById('collegehub-auth-modal')) return;

    // Don't inject on standalone login or admin pages where the full card is already the center
    const path = window.location.pathname.toLowerCase();
    if (path.includes('login') || path.includes('signin') || path.includes('signup') || path.includes('admin')) {
      return;
    }

    const modalWrapper = document.createElement('div');
    modalWrapper.id = 'collegehub-auth-modal';
    modalWrapper.className = 'fixed inset-0 z-[100] flex items-center justify-center p-4 bg-primary/60 backdrop-blur-md opacity-0 pointer-events-none transition-all duration-300';
    
    modalWrapper.innerHTML = `
      <div id="modal-card" class="w-full max-w-md bg-surface-container-lowest rounded-3xl p-6 sm:p-8 shadow-[0_20px_60px_rgba(0,0,0,0.18)] border border-surface-container-high relative transform scale-95 transition-all duration-300">
        
        <!-- Close Button -->
        <button type="button" onclick="CollegeHubAuth.closeAuthModal()" class="absolute top-5 right-5 w-8 h-8 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface-variant flex items-center justify-center transition-colors" title="Close dialog">
          <span class="material-symbols-outlined text-lg">close</span>
        </button>

        <!-- Brand Icon -->
        <div class="text-center mb-5">
          <div class="w-12 h-12 rounded-2xl bg-secondary-container text-on-secondary-container mx-auto flex items-center justify-center mb-3 shadow-xs">
            <span class="material-symbols-outlined text-2xl">school</span>
          </div>
          <h2 class="text-xl sm:text-2xl font-extrabold text-primary tracking-tight" id="modal-title">Welcome to CollegeHub</h2>
          <p class="text-xs text-on-surface-variant mt-1" id="modal-subtitle">Log in or create a student account to access personalized college recommendations.</p>
        </div>

        <!-- Mode Toggle Tabs (Login vs Signup) -->
        <div class="flex items-center p-1 bg-surface-container-low rounded-xl mb-5 border border-surface-container-high/60">
          <button type="button" id="tab-modal-login" onclick="CollegeHubAuth.switchAuthModalTab('login')" class="flex-1 py-2 text-xs font-bold rounded-lg transition-all bg-surface-container-lowest text-primary shadow-xs">
            Log In
          </button>
          <button type="button" id="tab-modal-signup" onclick="CollegeHubAuth.switchAuthModalTab('signup')" class="flex-1 py-2 text-xs font-semibold rounded-lg transition-all text-on-surface-variant hover:text-on-surface">
            Sign Up
          </button>
        </div>

        <!-- Dynamic Role Selector inside modal -->
        <div class="mb-4 flex items-center gap-1.5 p-1 bg-surface-container rounded-lg text-xs" id="modal-role-selector">
          <button type="button" onclick="CollegeHubAuth.setModalRole('student')" id="modal-role-student" class="flex-1 py-1.5 px-2 rounded-md font-bold text-center transition-all bg-surface-container-lowest text-primary shadow-xs">
            Student
          </button>
          <button type="button" onclick="CollegeHubAuth.setModalRole('parent')" id="modal-role-parent" class="flex-1 py-1.5 px-2 rounded-md font-semibold text-center transition-all text-on-surface-variant hover:text-on-surface">
            Parent
          </button>
        </div>

        <!-- Google Quick Sign-In Button -->
        <button 
          type="button" 
          onclick="CollegeHubAuth.signInWithGoogle()" 
          class="w-full py-2.5 px-4 rounded-xl bg-surface-container-low hover:bg-surface-container text-on-surface text-xs sm:text-sm font-bold border border-surface-container-high transition-all flex items-center justify-center gap-2.5 mb-3.5 shadow-2xs hover:shadow-xs group cursor-pointer"
        >
          <svg class="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" viewBox="0 0 24 24">
            <path d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.66v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.15z" fill="#4285F4"></path>
            <path d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.14C3.26 21.36 7.33 24 12 24z" fill="#34A853"></path>
            <path d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.59H1.25C.45 8.18 0 10.02 0 12s.45 3.82 1.25 5.41l4.03-3.14z" fill="#FBBC05"></path>
            <path d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.59l4.03 3.14c.95-2.83 3.6-4.98 6.72-4.98z" fill="#EA4335"></path>
          </svg>
          <span>Continue with Google</span>
        </button>

        <!-- Divider -->
        <div class="relative mb-4 flex items-center justify-center">
          <div class="w-full h-px bg-surface-container-high"></div>
          <span class="absolute px-3 bg-surface-container-lowest text-[10px] uppercase font-bold text-on-surface-variant tracking-wider">
            or use credentials
          </span>
        </div>

        <!-- Alert Box -->
        <div id="modal-auth-alert" class="hidden"></div>

        <!-- 1. LOGIN FORM PANEL -->
        <form id="modal-login-form" class="space-y-3.5" onsubmit="CollegeHubAuth.handleLoginSubmit(event, CollegeHubAuth.getModalRole())">
          <div>
            <label class="block text-[11px] font-bold text-primary mb-1" for="modal-login-identifier">Email / Applicant ID</label>
            <div class="relative">
              <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-base">mail</span>
              <input 
                class="w-full pl-9 pr-3 py-2 bg-surface border border-outline-variant rounded-xl text-xs sm:text-sm text-primary placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-secondary/30 focus:border-secondary transition-all" 
                id="modal-login-identifier" 
                placeholder="name@example.com" 
                required 
                type="text"
              >
            </div>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="block text-[11px] font-bold text-primary" for="modal-login-password">Password</label>
              <button type="button" onclick="CollegeHubAuth.openForgotPasswordModal(document.getElementById('modal-login-identifier')?.value)" class="text-[10px] text-secondary font-bold hover:underline">Forgot?</button>
            </div>
            <div class="relative">
              <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-base">lock</span>
              <input 
                class="w-full pl-9 pr-9 py-2 bg-surface border border-outline-variant rounded-xl text-xs sm:text-sm text-primary placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-secondary/30 focus:border-secondary transition-all" 
                id="modal-login-password" 
                placeholder="••••••••••••" 
                required 
                type="password"
              >
              <button 
                type="button" 
                onclick="CollegeHubAuth.toggleModalPass('modal-login-password', this)" 
                class="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-primary transition-colors focus:outline-none"
              >
                <span class="material-symbols-outlined text-base">visibility</span>
              </button>
            </div>
          </div>

          <button 
            type="submit" 
            id="modal-login-submit-btn" 
            class="w-full py-2.5 px-4 rounded-xl bg-primary text-white font-bold text-xs sm:text-sm shadow-md hover:bg-primary-container active:scale-[0.99] transition-all flex items-center justify-center gap-2 mt-1"
          >
            <span>Log In &amp; Continue</span>
            <span class="material-symbols-outlined text-base">arrow_forward</span>
          </button>
        </form>

        <!-- 2. SIGN UP FORM PANEL (Hidden by default) -->
        <form id="modal-signup-form" class="space-y-3.5 hidden" onsubmit="CollegeHubAuth.handleRegisterSubmit(event, CollegeHubAuth.getModalRole())">
          <div>
            <label class="block text-[11px] font-bold text-primary mb-1" for="modal-signup-fullname">Full Name</label>
            <div class="relative">
              <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-base">person</span>
              <input 
                class="w-full pl-9 pr-3 py-2 bg-surface border border-outline-variant rounded-xl text-xs sm:text-sm text-primary placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-secondary/30 focus:border-secondary transition-all" 
                id="modal-signup-fullname" 
                placeholder="e.g. Full Name" 
                required 
                type="text"
              >
            </div>
          </div>

          <div>
            <label class="block text-[11px] font-bold text-primary mb-1" for="modal-signup-email">Email Address</label>
            <div class="relative">
              <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-base">mail</span>
              <input 
                class="w-full pl-9 pr-3 py-2 bg-surface border border-outline-variant rounded-xl text-xs sm:text-sm text-primary placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-secondary/30 focus:border-secondary transition-all" 
                id="modal-signup-email" 
                placeholder="student@example.com" 
                required 
                type="email"
              >
            </div>
          </div>

          <div>
            <label class="block text-[11px] font-bold text-primary mb-1" for="modal-signup-password">Create Password</label>
            <div class="relative">
              <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-base">lock</span>
              <input 
                class="w-full pl-9 pr-9 py-2 bg-surface border border-outline-variant rounded-xl text-xs sm:text-sm text-primary placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-secondary/30 focus:border-secondary transition-all" 
                id="modal-signup-password" 
                placeholder="At least 6 characters" 
                required 
                type="password"
              >
              <button 
                type="button" 
                onclick="CollegeHubAuth.toggleModalPass('modal-signup-password', this)" 
                class="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-primary transition-colors focus:outline-none"
              >
                <span class="material-symbols-outlined text-base">visibility</span>
              </button>
            </div>
          </div>

          <button 
            type="submit" 
            id="modal-signup-submit-btn" 
            class="w-full py-2.5 px-4 rounded-xl bg-secondary text-white font-bold text-xs sm:text-sm shadow-md hover:bg-secondary/90 active:scale-[0.99] transition-all flex items-center justify-center gap-2 mt-1"
          >
            <span>Create Free Account</span>
            <span class="material-symbols-outlined text-base">check_circle</span>
          </button>
        </form>

        <!-- Footer Guest Action -->
        <div class="mt-5 pt-3.5 border-t border-surface-container flex items-center justify-between text-xs text-on-surface-variant">
          <button type="button" onclick="CollegeHubAuth.closeAuthModal()" class="text-on-surface-variant hover:text-primary transition-colors">
            Continue as Guest &rarr;
          </button>
          <a href="/login" class="text-secondary font-bold hover:underline">
            Full Portal Page
          </a>
        </div>

      </div>
    `;

    document.body.appendChild(modalWrapper);
  }

  function openAuthModal(mode) {
    injectAuthModal();
    const modal = document.getElementById('collegehub-auth-modal');
    const card = document.getElementById('modal-card');
    if (!modal || !card) return;

    if (mode) switchAuthModalTab(mode);

    modal.classList.remove('opacity-0', 'pointer-events-none');
    modal.classList.add('opacity-100', 'pointer-events-auto');
    card.classList.remove('scale-95');
    card.classList.add('scale-100');
  }

  function closeAuthModal() {
    const modal = document.getElementById('collegehub-auth-modal');
    const card = document.getElementById('modal-card');
    if (!modal) return;

    sessionStorage.setItem(DISMISSED_KEY, 'true');

    modal.classList.remove('opacity-100', 'pointer-events-auto');
    modal.classList.add('opacity-0', 'pointer-events-none');
    if (card) {
      card.classList.remove('scale-100');
      card.classList.add('scale-95');
    }
  }

  function switchAuthModalTab(tabKey) {
    currentModalTab = tabKey;
    const tabLogin = document.getElementById('tab-modal-login');
    const tabSignup = document.getElementById('tab-modal-signup');
    const formLogin = document.getElementById('modal-login-form');
    const formSignup = document.getElementById('modal-signup-form');
    const title = document.getElementById('modal-title');
    const subtitle = document.getElementById('modal-subtitle');
    const alertBox = document.getElementById('modal-auth-alert');

    if (alertBox) alertBox.classList.add('hidden');

    if (tabKey === 'login') {
      if (tabLogin) tabLogin.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition-all bg-surface-container-lowest text-primary shadow-xs';
      if (tabSignup) tabSignup.className = 'flex-1 py-2 text-xs font-semibold rounded-lg transition-all text-on-surface-variant hover:text-on-surface';
      if (formLogin) formLogin.classList.remove('hidden');
      if (formSignup) formSignup.classList.add('hidden');
      if (title) title.textContent = 'Log in to CollegeHub';
      if (subtitle) subtitle.textContent = 'Access verified cutoffs, application milestones, and admissions status.';
    } else {
      if (tabSignup) tabSignup.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition-all bg-surface-container-lowest text-primary shadow-xs';
      if (tabLogin) tabLogin.className = 'flex-1 py-2 text-xs font-semibold rounded-lg transition-all text-on-surface-variant hover:text-on-surface';
      if (formSignup) formSignup.classList.remove('hidden');
      if (formLogin) formLogin.classList.add('hidden');
      if (title) title.textContent = 'Create Student Account';
      if (subtitle) subtitle.textContent = 'Get personalized admissions recommendations, cutoff guidance, and chat support.';
    }
  }

  function setModalRole(role) {
    modalActiveRole = role;
    const btnStudent = document.getElementById('modal-role-student');
    const btnParent = document.getElementById('modal-role-parent');

    if (btnStudent && btnParent) {
      if (role === 'student') {
        btnStudent.className = 'flex-1 py-1.5 px-2 rounded-md font-bold text-center transition-all bg-surface-container-lowest text-primary shadow-xs';
        btnParent.className = 'flex-1 py-1.5 px-2 rounded-md font-semibold text-center transition-all text-on-surface-variant hover:text-on-surface';
      } else {
        btnParent.className = 'flex-1 py-1.5 px-2 rounded-md font-bold text-center transition-all bg-surface-container-lowest text-primary shadow-xs';
        btnStudent.className = 'flex-1 py-1.5 px-2 rounded-md font-semibold text-center transition-all text-on-surface-variant hover:text-on-surface';
      }
    }
  }

  function getModalRole() {
    return modalActiveRole || 'student';
  }

  function quickFillModal() {
    // Demo auto-fill removed
  }

  function toggleModalPass(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const icon = btn.querySelector('.material-symbols-outlined');
    if (input.type === 'password') {
      input.type = 'text';
      if (icon) icon.textContent = 'visibility_off';
    } else {
      input.type = 'password';
      if (icon) icon.textContent = 'visibility';
    }
  }

  /**
   * Auto Popup trigger when visiting website:
   * If visitor is not logged in and hasn't dismissed in current tab, pop up!
   */
  function checkAndTriggerAutoPopup() {
    // If user is already logged in, no need to interrupt
    if (isLoggedIn()) return;

    // Check if dismissed in this browsing tab
    if (sessionStorage.getItem(DISMISSED_KEY) === 'true') return;

    // Only auto-trigger on the public landing page or public pages, not on dedicated auth pages
    const path = window.location.pathname.toLowerCase();
    if (path === '/' || path.endsWith('index.html') || path === '') {
      setTimeout(() => {
        openAuthModal('login');
      }, 400);
    }
  }

  /**
   * Scans document and updates all user display elements with current session info.
   */
  function updateDOM() {
    const user = getUser();
    const logged = isLoggedIn();

    if (logged && user) {
      document.querySelectorAll('[data-user-name]').forEach(el => {
        el.textContent = user.name || 'Student Profile';
      });

      document.querySelectorAll('[data-user-email]').forEach(el => {
        el.textContent = user.email || 'student@example.com';
      });

      document.querySelectorAll('[data-user-initials]').forEach(el => {
        el.textContent = user.initials || 'ST';
      });

      document.querySelectorAll('[data-user-id]').forEach(el => {
        el.textContent = user.applicant_id || user.id || '#CH-2025-0001';
      });

      document.querySelectorAll('[data-user-role]').forEach(el => {
        el.textContent = user.role_label || user.role || 'Student Candidate';
      });
    } else {
      document.querySelectorAll('[data-user-name]').forEach(el => {
        el.textContent = 'Student Profile';
      });

      document.querySelectorAll('[data-user-email]').forEach(el => {
        el.textContent = 'student@example.com';
      });

      document.querySelectorAll('[data-user-initials]').forEach(el => {
        el.textContent = 'ST';
      });

      document.querySelectorAll('[data-user-id]').forEach(el => {
        el.textContent = '#CH-2025-0001';
      });

      document.querySelectorAll('[data-user-role]').forEach(el => {
        el.textContent = 'Student Candidate';
      });
    }

    // Update header login/join buttons or profile capsules
    document.querySelectorAll('.auth-trigger-btn').forEach(btn => {
      if (logged && user) {
        btn.innerHTML = `<span class="material-symbols-outlined text-base">account_circle</span><span>${user.name}</span>`;
        btn.onclick = () => window.location.href = '/profile';
      } else {
        btn.innerHTML = `<span class="material-symbols-outlined text-base">account_circle</span><span>Sign In / Join</span>`;
        btn.onclick = () => openAuthModal('login');
      }
    });
  }

  /* ==========================================================================
     GOOGLE SIGN-IN INTEGRATION
     ========================================================================== */

  function signInWithGoogle(customEmail, customName) {
    // If called with explicit email (e.g. from tests or scripts)
    if (customEmail && typeof customEmail === 'string' && customEmail.includes('@')) {
      const email = customEmail.trim();
      const name = customName || email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      fetch('/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          name: name,
          picture: 'https://lh3.googleusercontent.com/a/default-user=s96-c',
          role: window.activeRole || getModalRole() || 'student'
        })
      })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'success') {
          setUser(data.user);
          window.location.href = data.redirect_url || '/profile';
        }
      })
      .catch(err => console.error(err));
      return;
    }

    // Standard redirect to Google OAuth login flow (accounts.google.com)
    const role = window.activeRole || getModalRole() || 'student';
    window.location.href = `/api/auth/google/login?role=${encodeURIComponent(role)}`;
  }

  function openGoogleChooserModal() {
    signInWithGoogle();
  }

  function closeGoogleChooserModal() {
    // Compatibility stub
  }

  /* ==========================================================================
     PASSWORD RESET WITH VERIFICATION CODE FLOW
     ========================================================================== */

  let activeResetEmail = '';
  let activeResetCode = '';

  function injectForgotPasswordModal() {
    if (document.getElementById('collegehub-forgot-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'collegehub-forgot-modal';
    modal.className = 'fixed inset-0 z-[160] flex items-center justify-center p-4 bg-primary/70 backdrop-blur-md opacity-0 pointer-events-none transition-all duration-300';
    modal.innerHTML = `
      <div id="forgot-modal-card" class="w-full max-w-md bg-surface-container-lowest rounded-3xl p-6 sm:p-8 shadow-[0_20px_60px_rgba(0,0,0,0.25)] border border-surface-container-high relative transform scale-95 transition-all duration-300 text-on-surface">
        
        <!-- Close Button -->
        <button type="button" onclick="CollegeHubAuth.closeForgotPasswordModal()" class="absolute top-5 right-5 w-8 h-8 rounded-full bg-surface-container hover:bg-surface-container-high text-on-surface-variant flex items-center justify-center transition-colors" title="Close dialog">
          <span class="material-symbols-outlined text-lg">close</span>
        </button>

        <!-- Brand Icon -->
        <div class="text-center mb-5">
          <div class="w-12 h-12 rounded-2xl bg-secondary-container text-on-secondary-container mx-auto flex items-center justify-center mb-3 shadow-xs">
            <span class="material-symbols-outlined text-2xl">mark_email_read</span>
          </div>
          <h2 class="text-xl sm:text-2xl font-extrabold text-primary tracking-tight">Reset Account Password</h2>
          <p class="text-xs text-on-surface-variant mt-1">We will send a 6-digit verification code to your registered email.</p>
        </div>

        <!-- Alert Notification Box -->
        <div id="forgot-alert-box" class="hidden mb-4 p-3 rounded-xl text-xs font-semibold"></div>

        <!-- STEP 1: Enter Email & Request Code -->
        <div id="forgot-step-1" class="space-y-4">
          <div>
            <label class="block text-xs font-bold text-primary mb-1.5" for="forgot-email-input">Your Registered Email Address</label>
            <div class="relative">
              <span class="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-on-surface-variant text-base">mail</span>
              <input 
                type="email" 
                id="forgot-email-input" 
                placeholder="name@example.com" 
                class="w-full pl-10 pr-4 py-2.5 bg-surface border border-outline-variant rounded-xl text-xs sm:text-sm text-primary placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-secondary/30 focus:border-secondary transition-all"
                required
              >
            </div>
          </div>

          <button 
            type="button" 
            id="send-code-btn"
            onclick="CollegeHubAuth.sendVerificationCode()"
            class="w-full py-3 px-5 rounded-xl bg-primary text-white font-bold text-xs sm:text-sm shadow-md hover:bg-primary-container transition-all flex items-center justify-center gap-2 cursor-pointer"
          >
            <span class="material-symbols-outlined text-base">send</span>
            <span>Send 6-Digit Verification Code</span>
          </button>
        </div>

        <!-- STEP 2: Enter Verification Code & New Password -->
        <div id="forgot-step-2" class="space-y-4 hidden">
          <!-- Code info notice -->
          <div class="p-3.5 rounded-2xl bg-secondary/10 border border-secondary/30 text-xs text-secondary dark:text-teal-300 space-y-1.5">
            <div class="font-bold flex items-center gap-1.5">
              <span class="material-symbols-outlined text-sm">mark_email_read</span>
              <span>Verification email sent to: <span id="display-target-email" class="font-extrabold text-primary underline"></span></span>
            </div>
            <div class="text-[11px] text-on-surface-variant leading-relaxed">
              We sent a 6-digit verification code to your Gmail inbox. Please check your inbox (and spam folder), then enter the code below.
            </div>
          </div>

          <div>
            <label class="block text-xs font-bold text-primary mb-1.5" for="verification-code-input">6-Digit Verification Code</label>
            <div class="relative">
              <span class="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-on-surface-variant text-base">pin</span>
              <input 
                type="text" 
                id="verification-code-input" 
                maxlength="6" 
                placeholder="000000" 
                autocomplete="one-time-code"
                class="w-full pl-10 pr-4 py-2.5 bg-surface border border-outline-variant rounded-xl text-center font-mono font-bold tracking-widest text-lg sm:text-xl text-primary focus:outline-none focus:ring-2 focus:ring-secondary/30 focus:border-secondary transition-all"
                required
              >
            </div>
          </div>

          <div>
            <label class="block text-xs font-bold text-primary mb-1.5" for="new-password-input">New Password</label>
            <div class="relative">
              <span class="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-on-surface-variant text-base">lock</span>
              <input 
                type="password" 
                id="new-password-input" 
                placeholder="At least 6 characters" 
                class="w-full pl-10 pr-10 py-2.5 bg-surface border border-outline-variant rounded-xl text-xs sm:text-sm text-primary placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-secondary/30 focus:border-secondary transition-all"
                required
              >
              <button 
                type="button" 
                onclick="CollegeHubAuth.toggleModalPass('new-password-input', this)" 
                class="absolute right-3.5 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-primary transition-colors focus:outline-none"
              >
                <span class="material-symbols-outlined text-base">visibility</span>
              </button>
            </div>
          </div>

          <div class="flex items-center justify-between text-xs pt-1">
            <button 
              type="button" 
              onclick="CollegeHubAuth.sendVerificationCode()" 
              class="text-xs text-secondary font-bold hover:underline"
            >
              Resend Code
            </button>
          </div>

          <button 
            type="button" 
            id="reset-pass-btn"
            onclick="CollegeHubAuth.submitPasswordReset()"
            class="w-full py-3 px-5 rounded-xl bg-secondary text-white font-bold text-xs sm:text-sm shadow-md hover:bg-secondary/90 transition-all flex items-center justify-center gap-2 cursor-pointer"
          >
            <span class="material-symbols-outlined text-base">lock_reset</span>
            <span>Verify Code &amp; Reset Password</span>
          </button>
        </div>

        <!-- STEP 3: Success State -->
        <div id="forgot-step-3" class="space-y-4 hidden text-center py-2">
          <div class="w-14 h-14 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 mx-auto flex items-center justify-center">
            <span class="material-symbols-outlined text-3xl">check_circle</span>
          </div>
          <h3 class="text-lg font-bold text-primary">Password Reset Successful!</h3>
          <p class="text-xs text-on-surface-variant">Your account password has been updated. You can now log in with your new credentials.</p>
          <button 
            type="button" 
            onclick="CollegeHubAuth.closeForgotPasswordModal();" 
            class="w-full py-2.5 px-4 rounded-xl bg-primary text-white font-bold text-xs sm:text-sm shadow-md hover:bg-primary-container transition-all cursor-pointer"
          >
            Return to Log In
          </button>
        </div>

        <div class="mt-5 pt-3.5 border-t border-surface-container flex items-center justify-between text-xs text-on-surface-variant">
          <button type="button" onclick="CollegeHubAuth.closeForgotPasswordModal()" class="text-on-surface-variant hover:text-primary transition-colors">
            &larr; Back to Log In
          </button>
        </div>

      </div>
    `;
    document.body.appendChild(modal);
  }

  function openForgotPasswordModal(prefillEmail) {
    closeGoogleChooserModal();
    injectForgotPasswordModal();
    const modal = document.getElementById('collegehub-forgot-modal');
    const card = document.getElementById('forgot-modal-card');
    if (!modal || !card) return;

    // Reset view to Step 1
    document.getElementById('forgot-step-1')?.classList.remove('hidden');
    document.getElementById('forgot-step-2')?.classList.add('hidden');
    document.getElementById('forgot-step-3')?.classList.add('hidden');
    const alertBox = document.getElementById('forgot-alert-box');
    if (alertBox) alertBox.classList.add('hidden');

    const emailInput = document.getElementById('forgot-email-input');
    if (emailInput) {
      emailInput.value = prefillEmail || '';
    }

    modal.classList.remove('opacity-0', 'pointer-events-none');
    modal.classList.add('opacity-100', 'pointer-events-auto');
    card.classList.remove('scale-95');
    card.classList.add('scale-100');
  }

  function closeForgotPasswordModal() {
    const modal = document.getElementById('collegehub-forgot-modal');
    const card = document.getElementById('forgot-modal-card');
    if (!modal) return;
    modal.classList.remove('opacity-100', 'pointer-events-auto');
    modal.classList.add('opacity-0', 'pointer-events-none');
    if (card) {
      card.classList.remove('scale-100');
      card.classList.add('scale-95');
    }
  }

  async function sendVerificationCode() {
    const emailInput = document.getElementById('forgot-email-input');
    const email = (emailInput ? emailInput.value : '').trim().toLowerCase();
    const btn = document.getElementById('send-code-btn');
    const alertBox = document.getElementById('forgot-alert-box');

    if (!email || !email.includes('@')) {
      if (alertBox) {
        alertBox.className = 'mb-4 p-3 rounded-xl bg-error-container text-on-error-container text-xs font-semibold flex items-center gap-2';
        alertBox.innerHTML = '<span class="material-symbols-outlined text-base shrink-0">error</span><span>Please enter a valid email address.</span>';
        alertBox.classList.remove('hidden');
      }
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="material-symbols-outlined text-base animate-spin">progress_activity</span><span>Generating verification code...</span>';
    }

    try {
      const resp = await fetch('/api/auth/send-reset-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
      });
      const data = await resp.json();

      if (resp.ok && data.status === 'success') {
        activeResetEmail = email;

        // Transition to Step 2
        document.getElementById('forgot-step-1')?.classList.add('hidden');
        document.getElementById('forgot-step-2')?.classList.remove('hidden');
        const disp = document.getElementById('display-target-email');
        if (disp) disp.textContent = email;

        // Reset verification code field so user types the code sent to their Gmail
        const codeInput = document.getElementById('verification-code-input');
        if (codeInput) {
          codeInput.value = '';
          setTimeout(() => codeInput.focus(), 150);
        }

        if (alertBox) {
          alertBox.className = 'mb-4 p-3 rounded-xl bg-secondary-container text-on-secondary-container text-xs font-semibold flex items-center gap-2';
          alertBox.innerHTML = `<span class="material-symbols-outlined text-base shrink-0">mark_email_read</span><span>${data.message}</span>`;
          alertBox.classList.remove('hidden');
        }
      } else {
        if (alertBox) {
          alertBox.className = 'mb-4 p-3 rounded-xl bg-error-container text-on-error-container text-xs font-semibold flex items-center gap-2';
          alertBox.innerHTML = `<span class="material-symbols-outlined text-base shrink-0">error</span><span>${data.message || 'Failed to send code.'}</span>`;
          alertBox.classList.remove('hidden');
        }
      }
    } catch (err) {
      console.error('Send reset code error:', err);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined text-base">send</span><span>Send 6-Digit Verification Code</span>';
      }
    }
  }

  async function submitPasswordReset() {
    const codeInput = document.getElementById('verification-code-input');
    const passInput = document.getElementById('new-password-input');
    const btn = document.getElementById('reset-pass-btn');
    const alertBox = document.getElementById('forgot-alert-box');

    const code = (codeInput ? codeInput.value : '').trim();
    const newPass = (passInput ? passInput.value : '').trim();

    if (!code || code.length !== 6) {
      if (alertBox) {
        alertBox.className = 'mb-4 p-3 rounded-xl bg-error-container text-on-error-container text-xs font-semibold flex items-center gap-2';
        alertBox.innerHTML = '<span class="material-symbols-outlined text-base shrink-0">error</span><span>Please enter the 6-digit verification code.</span>';
        alertBox.classList.remove('hidden');
      }
      return;
    }

    if (!newPass || newPass.length < 6) {
      if (alertBox) {
        alertBox.className = 'mb-4 p-3 rounded-xl bg-error-container text-on-error-container text-xs font-semibold flex items-center gap-2';
        alertBox.innerHTML = '<span class="material-symbols-outlined text-base shrink-0">error</span><span>New password must be at least 6 characters.</span>';
        alertBox.classList.remove('hidden');
      }
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="material-symbols-outlined text-base animate-spin">progress_activity</span><span>Updating password...</span>';
    }

    try {
      const resp = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: activeResetEmail || document.getElementById('forgot-email-input')?.value,
          code: code,
          new_password: newPass
        })
      });
      const data = await resp.json();

      if (resp.ok && data.status === 'success') {
        // Transition to Step 3
        document.getElementById('forgot-step-2')?.classList.add('hidden');
        document.getElementById('forgot-step-3')?.classList.remove('hidden');
        if (alertBox) alertBox.classList.add('hidden');

        // If on standalone login page, update password field
        const loginPass = document.getElementById('auth-password') || document.getElementById('modal-login-password');
        if (loginPass) loginPass.value = newPass;
      } else {
        if (alertBox) {
          alertBox.className = 'mb-4 p-3 rounded-xl bg-error-container text-on-error-container text-xs font-semibold flex items-center gap-2';
          alertBox.innerHTML = `<span class="material-symbols-outlined text-base shrink-0">error</span><span>${data.message || 'Reset failed.'}</span>`;
          alertBox.classList.remove('hidden');
        }
      }
    } catch (err) {
      console.error('Password reset error:', err);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-symbols-outlined text-base">lock_reset</span><span>Verify Code &amp; Reset Password</span>';
      }
    }
  }

  function init() {
    updateDOM();
    injectAuthModal();
    injectForgotPasswordModal();
    checkAndTriggerAutoPopup();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return {
    getUser: getUser,
    setUser: setUser,
    isLoggedIn: isLoggedIn,
    logout: logout,
    handleLoginSubmit: handleLoginSubmit,
    handleRegisterSubmit: handleRegisterSubmit,
    openAuthModal: openAuthModal,
    closeAuthModal: closeAuthModal,
    switchAuthModalTab: switchAuthModalTab,
    setModalRole: setModalRole,
    getModalRole: getModalRole,
    quickFillModal: quickFillModal,
    toggleModalPass: toggleModalPass,
    updateDOM: updateDOM,
    signInWithGoogle: signInWithGoogle,
    openGoogleChooserModal: openGoogleChooserModal,
    closeGoogleChooserModal: closeGoogleChooserModal,
    openForgotPasswordModal: openForgotPasswordModal,
    closeForgotPasswordModal: closeForgotPasswordModal,
    sendVerificationCode: sendVerificationCode,
    submitPasswordReset: submitPasswordReset
  };
})();
