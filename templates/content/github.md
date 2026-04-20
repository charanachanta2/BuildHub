# 🚀 GitHub Basics Guide

---

## 🟢 Step 1: Create a GitHub Account

GitHub is the most important platform for developers. It is used to store, manage, and share code.

### Why GitHub matters:
- Acts as your developer portfolio
- Companies check your GitHub
- You can host projects
- You can collaborate

### Steps:
1. Go to https://github.com  
2. Click **Sign Up**  
3. Enter email, password, username  
4. Verify email  

💡 Use a professional username

---

## 🟡 Step 2: Complete Your Profile

Your profile is like your developer resume.

### Steps:
1. Go to Settings  
2. Add:
   - Profile picture  
   - Bio  
   - Location  

### Example Bio:
```
Aspiring Developer | Learning Web Dev | BuildHub 🚀
```

---

## 🔵 Step 3: Create Repository + Calculator

### Create Repo:
1. Click **New Repository**
2. Name: **calculator-project**
3. Public + Add README

---

### Add File → index.html

```html
<!DOCTYPE html>
<html>
<head>
  <title>Calculator</title>
  <style>
    body {
      display:flex;
      justify-content:center;
      align-items:center;
      height:100vh;
      background:#111;
      color:white;
    }
    .calc { background:#222; padding:20px; }
    input { width:100%; margin-bottom:10px; }
    button { width:22%; margin:2px; }
  </style>
</head>
<body>

<div class="calc">
  <input id="display" disabled>

  <button onclick="add('1')">1</button>
  <button onclick="add('2')">2</button>
  <button onclick="add('+')">+</button>
  <button onclick="calculate()">=</button>

</div>

<script>
function add(v){ document.getElementById('display').value+=v; }
function calculate(){
  document.getElementById('display').value =
  eval(document.getElementById('display').value);
}
</script>

</body>
</html>
```

Click **Commit Changes**

---

## 🟣 Step 4: Deploy using GitHub Pages

### Steps:
1. Go to repo → Settings  
2. Click **Pages**  
3. Select:
   - Branch: main  
   - Folder: root  
4. Save  

### Your site:
```
https://yourusername.github.io/calculator-project/
```

---

## 🟢 Step 5: Completed 🎉

You:
- Created GitHub account  
- Created repo  
- Added code  
- Deployed website  

🚀 You completed GitHub Basics!

---

## 🎁 BONUS (Real Developer Workflow)

Developers don’t use GitHub editor usually.

They use:

### VS Code + Terminal

```bash
git init
git add .
git commit -m "update"
git push
```

💡 This is how real developers work.

<a href="/complete/github" class="btn">Mark GitHub Complete</a>