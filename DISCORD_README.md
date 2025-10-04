# 🎮 **FRANCHISE PLAYER BOT - COMPLETE GUIDE** 🎮

## 📋 **OVERVIEW**
Welcome to the **Franchise Player Bot**! This bot helps manage your Madden franchise with points, player upgrades, streaming rewards, and trade calculations.

---

## 🎯 **POINTS SYSTEM**

### **📊 Check Your Points**
- `/checkstats` - View your current points
- `/checkstats @user` - View another user's points
- `/leaderboard` - See the top 20 players by points

### **⚡ Admin Commands** *(Admin/Commish Only)*
- `/addpoints @user amount` - Add points to a user
- `/removepoints @user amount` - Remove points from a user  
- `/clearpoints @user` - Reset a user's points to 0
- `/clearstreampoints @user` - Clear only stream points (keeps total points)

---

## 🃏 **PLAYER CARDS & UPGRADES**

### **🎴 View Your Cards**
- `/my_cards` - See all your player cards and upgrades

### **⬆️ Upgrade Players**
- `/upgrade` - Interactive upgrade system with dropdowns:
  1. **Select Position** (QB, RB, WR, TE, LT/RT, LG/RG, C, Edge, DT, LB, CB, S, FB, K, P)
  2. **Enter Player Name** (any name you want)
  3. **Choose Attribute** (position-specific attributes)
  4. **Select Points** (1-25 points, based on your balance)

### **⚠️ Important Notes:**
- **No attribute can exceed 90!**
- You need at least 2 total points to upgrade
- Each upgrade costs the points you select

### **🗑️ Admin Commands** *(Admin Only)*
- `/clear_cards @user` - Remove all player cards for a user

---

## 📺 **STREAMING SYSTEM**

### **🔗 Set Up Your Stream**
1. **Get your Twitch URL** (e.g., `https://www.twitch.tv/yourusername`)
2. **Register it**: `/addstream` - Enter your Twitch URL when prompted
3. **Verify**: `/mystream` - Check your registered link

### **🎮 Earn Stream Points**
- `/streamgame` - Start streaming Madden and earn points!
- `/streamdiscord` - Verify Discord streaming (Go Live or Screen Share)

### **📈 Stream Points System:**
- **Stream Points**: Separate counter (max 8 points from streaming)
- **Total Points**: Includes all points (stream + other activities)
- **After 8 stream points**: You can still stream, but no more stream points earned
- **Cooldown**: 45 minutes between stream point awards

### **📺 Stream Notifications:**
- Shows your Twitch profile picture
- Displays "Total Points: X | Stream Points: Y/8"
- Auto-cross-posts to designated stream channel
- Hardcoded Discord channel link for `/streamdiscord`

### **⚙️ Admin Commands** *(Admin Only)*
- `/setstreamchannel #channel` - Set designated stream announcement channel
- `/streamchannel` - View current designated stream channel
- `/activestreams` - Show currently active streams

---

## 💰 **TRADE CALCULATOR**

### **🧮 Calculate Values**
- `/calc_player "Player Name"` - Get a player's trade value
- `/calc_pick year round` - Calculate draft pick value (e.g., `/calc_pick 2024 1`)

### **⚖️ Compare Trades**
- `/trade` - Compare trade values between teams
- `/tradecommittee` - Advanced AI-powered trade analysis

### **🔧 Debug** *(Admin Only)*
- `/test_values` - Test player and pick values

---

## 🏈 **GAME MANAGEMENT**

### **🏆 Game of the Week**
- `/gotw` - Manage Game of the Week system

### **📅 NFL Schedule**
- `/nfl` - NFL Schedule management commands

---

## 🎯 **QUICK START GUIDE**

### **For New Users:**
1. **Check your points**: `/checkstats`
2. **Set up streaming**: `/addstream` → Enter your Twitch URL
3. **Start upgrading**: `/upgrade` → Follow the interactive prompts
4. **View your progress**: `/my_cards`

### **For Streamers:**
1. **Register your stream**: `/addstream` → Enter Twitch URL
2. **Start streaming**: `/streamgame` or `/streamdiscord`
3. **Earn points**: Stream for 45+ minutes to earn points
4. **Track progress**: Check `/checkstats` for "Stream Points: X/8"

### **For Traders:**
1. **Calculate player values**: `/calc_player "Player Name"`
2. **Compare trades**: `/trade`
3. **Advanced analysis**: `/tradecommittee`

---

## 🚨 **IMPORTANT RULES**

### **⚠️ Upgrade Limits:**
- **No attribute can exceed 90**
- **Minimum 2 total points required to upgrade**
- **Points spent = points deducted from your balance**

### **📺 Streaming Rules:**
- **45-minute cooldown** between stream point awards
- **Maximum 8 stream points** (streaming still works after limit)
- **Must be actively streaming** Madden or using Discord streaming

### **👑 Admin Permissions:**
- **Admin/Commish**: Can add/remove points, clear cards, manage streams
- **Regular Users**: Can upgrade, stream, view stats

---

## 🆘 **NEED HELP?**

### **Common Issues:**
- **"Interaction failed"**: Try the command again
- **"No attributes available"**: Make sure you selected a valid position
- **"Not enough points"**: Check your balance with `/checkstats`
- **"Attribute over 90"**: Reduce the amount of points you're spending

### **Still Having Issues?**
Contact an admin or commish for assistance!

---

## 🎉 **ENJOY YOUR FRANCHISE!**

**Happy gaming and good luck with your franchise!** 🏈✨

*Last Updated: October 2024*
