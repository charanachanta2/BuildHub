function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("active");
}

function toggleNotif() {
  let dropdown = document.getElementById("notifDropdown");
  dropdown.classList.toggle("hidden");

  fetch("/get_notifications")
    .then(res => res.json())
    .then(data => {
      let html = "";

      data.notifications.forEach(n => {
        html += `
          <div class="notif-item">
            <span>${n.message}</span>
            <span class="delete-btn" onclick="deleteNotif('${n._id}')">❌</span>
          </div>
        `;
      });

      document.getElementById("notifList").innerHTML =
        html || "No notifications";
    });
}

function deleteNotif(id) {
  fetch("/delete_notification/" + id, {
    method: "POST"
  }).then(() => {
    toggleNotif(); // refresh
    toggleNotif();
  });
}

// profile toggle
function toggleMenu() {
  document.getElementById("profileDropdown").classList.toggle("hidden");
}

// close dropdowns
document.addEventListener("click", function(e) {
  if (!e.target.closest(".notif-menu")) {
    document.getElementById("notifDropdown").classList.add("hidden");
  }
  if (!e.target.closest(".profile-menu")) {
    document.getElementById("profileDropdown").classList.add("hidden");
  }
});

async function loadNotifications() {
  const res = await fetch("/get_notifications");
  const data = await res.json();

  const list = document.getElementById("notif-list");
  const count = document.getElementById("notif-count");

  if (!list || !count) return;

  list.innerHTML = "";
  count.innerText = data.notifications.length;

  data.notifications.forEach(n => {
    const div = document.createElement("div");
    div.innerHTML = `<a href="/project/${n.project_id}">${n.message}</a>`;
    list.appendChild(div);
  });
}

setInterval(loadNotifications, 5000);
loadNotifications();