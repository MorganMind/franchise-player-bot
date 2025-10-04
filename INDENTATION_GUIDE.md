# INDENTATION GUIDE - CRITICAL FOR PYTHON SYNTAX

## ⚠️ CRITICAL RULES - READ BEFORE EDITING PYTHON FILES

### 1. ALWAYS CHECK SYNTAX BEFORE COMMITTING
```bash
python3 -c "import ast; ast.parse(open('filename.py').read())"
```

### 2. INDENTATION RULES
- Python uses 4 spaces for indentation (NOT tabs)
- All code blocks must be properly indented
- When adding code inside existing blocks, match the surrounding indentation EXACTLY

### 3. COMMON INDENTATION ERRORS TO AVOID
- Mixing tabs and spaces
- Inconsistent indentation levels
- Missing indentation after `if`, `else`, `for`, `while`, `def`, `class`
- Incorrect indentation in nested blocks

### 4. BEFORE EVERY COMMIT
1. Run syntax check: `python3 -c "import ast; ast.parse(open('filename.py').read())"`
2. If it fails, fix the indentation
3. Test again until syntax is valid
4. Only then commit

### 5. WHEN EDITING LARGE BLOCKS
- Use search_replace with EXACT text matching
- Include enough context to ensure unique matches
- Double-check indentation after each edit

### 6. EMERGENCY FIXES
If you keep messing up indentation:
1. Read the file around the error line
2. Identify the correct indentation level
3. Use search_replace to fix the specific problematic lines
4. Test syntax immediately

## REAL-WORLD FIX EXAMPLE: gotw_system.py (FIXED)

### The Problem
The `teams_data = {` block in the `load_teams` method was incorrectly indented, causing `IndentationError: expected an indented block` at line 325.

### The Solution (How it was actually fixed)
The entire `teams_data` dictionary and all subsequent code within the `else:` block needed to be properly indented:

```python
# BEFORE (broken):
else:
    # Create default teams data if file doesn't exist
teams_data = {  # ❌ Wrong indentation - not inside else block
    "teams": [
        # ... team data ...
    ]
}

# AFTER (fixed):
else:
    # Create default teams data if file doesn't exist
    teams_data = {  # ✅ Correct indentation - properly inside else block
        "teams": [
            # ... team data ...
        ]
    }
    
    # Save teams data
    os.makedirs(os.path.dirname(self.teams_file), exist_ok=True)
    with open(self.teams_file, 'w') as f:
        json.dump(teams_data, f, indent=2)
    
    self.teams = {team['abbreviation']: team for team in teams_data['teams']}
    logger.info(f"Created default teams data with {len(self.teams)} teams")
```

### Key Points
- The `teams_data = {` line needed to be indented to match the `else:` block
- ALL code within the `else:` block must be consistently indented
- The `with open()` statement and `json.dump()` call also needed proper indentation
- This fix allowed the GOTW system cog to load successfully

## PREVENTION
- Always test syntax before pushing: `python3 -c "import ast; ast.parse(open('filename.py').read())"`
- Use consistent 4-space indentation
- When in doubt, copy indentation from working lines above
- Pay special attention to large code blocks and nested structures
