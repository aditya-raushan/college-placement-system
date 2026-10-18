// Client-side helpers. Server-side validation is still the real protection.
document.addEventListener("DOMContentLoaded", function () {
  // Bootstrap validation styling + password match check
  document.querySelectorAll("form.needs-validation").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      form.querySelectorAll("[data-match]").forEach(function (field) {
        var other = form.querySelector("#" + field.dataset.match);
        field.setCustomValidity(other && field.value !== other.value ? "Mismatch" : "");
      });
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add("was-validated");
    });
  });

  // Confirmation before destructive / important actions
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.dataset.confirm)) {
        event.preventDefault();
      }
    });
  });

  // Success/info messages fade out; errors stay until dismissed
  document.querySelectorAll(".alert.auto-dismiss.alert-success, .alert.auto-dismiss.alert-info").forEach(function (el) {
    setTimeout(function () {
      var instance = bootstrap.Alert.getOrCreateInstance(el);
      instance.close();
    }, 4000);
  });
});