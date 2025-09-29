# 🚀 Render Deployment Guide

## Prerequisites

1. **GitHub Repository**: Make sure your code is pushed to a GitHub repository
2. **Render Account**: Sign up at [render.com](https://render.com)
3. **Discord Bot Token**: You'll need your Discord bot token from the Discord Developer Portal

## Step 1: Create a New Background Worker on Render

1. Go to your Render dashboard
2. Click "New +" → "Background Worker" (NOT Web Service)
3. Connect your GitHub repository
4. Select your repository and branch

## Step 2: Configure the Service

### Basic Settings
- **Name**: `franchise-player-bot` (or your preferred name)
- **Environment**: `Python 3`
- **Region**: Choose the closest to your users
- **Branch**: `main` (or your default branch)

### Build & Deploy Settings
- **Build Command**: `pip install -r madden_discord_bot/requirements.txt`
- **Start Command**: `cd madden_discord_bot && python3 bot.py`

**Important**: Background Workers don't need port configuration - they run continuously in the background.

### Advanced Settings
- **Instance Type**: `Starter` (free tier) or `Standard` for better performance
- **Auto-Deploy**: `Yes` (recommended)

## Step 3: Environment Variables

Add these environment variables in the Render dashboard:

### Required Variables
```
DISCORD_TOKEN=your_discord_bot_token_here
```

### Optional Variables
```
OPENAI_API_KEY=your_openai_api_key_here
GUILD_ID=your_discord_server_id_here
```

### How to Add Environment Variables:
1. In your Render service dashboard
2. Go to "Environment" tab
3. Click "Add Environment Variable"
4. Add each variable with its value

## Step 4: Deploy

1. Click "Create Background Worker"
2. Render will automatically build and deploy your bot
3. Monitor the build logs for any issues
4. Once deployed, your bot will be online 24/7

## Step 5: Verify Deployment

1. Check the Render service logs to ensure the bot started successfully
2. Test the bot in your Discord server
3. Try some slash commands to verify functionality

## Important Notes

### Free Tier Limitations
- **Sleep Mode**: Free tier services sleep after 15 minutes of inactivity
- **Build Time**: Limited build minutes per month
- **Bandwidth**: Limited bandwidth usage

### Upgrading to Paid Plan
- **Always On**: Prevents the bot from sleeping
- **Better Performance**: More resources and faster response times
- **Custom Domains**: If you add web endpoints later

## Troubleshooting

### Common Issues

1. **Bot Not Responding**
   - Check Render service logs
   - Verify DISCORD_TOKEN is correct
   - Ensure bot has proper permissions in Discord

2. **Build Failures**
   - Check requirements.txt syntax
   - Verify Python version compatibility
   - Review build logs for specific errors

3. **Environment Variables**
   - Double-check variable names (case-sensitive)
   - Ensure no extra spaces in values
   - Redeploy after adding new variables

### Logs and Monitoring
- Use Render's built-in logging to monitor bot activity
- Set up alerts for service downtime
- Monitor resource usage in the dashboard

## Security Best Practices

1. **Never commit tokens to Git**
2. **Use environment variables for all secrets**
3. **Regularly rotate your Discord bot token**
4. **Monitor bot permissions in Discord**

## Cost Optimization

- Start with the free tier to test
- Monitor usage and upgrade only when needed
- Use efficient code to minimize resource usage
- Consider using webhooks for high-volume operations

## Support

- **Render Documentation**: [render.com/docs](https://render.com/docs)
- **Discord.py Documentation**: [discordpy.readthedocs.io](https://discordpy.readthedocs.io)
- **Discord Developer Portal**: [discord.com/developers](https://discord.com/developers)

---

Your bot should now be running 24/7 on Render! 🎉
