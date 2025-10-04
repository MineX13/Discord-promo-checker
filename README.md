# Discord Promo Code Checker

## Overview

This is a Discord promo/gift code validation tool that checks the validity and claim status of Discord gift codes without actually redeeming them. The application supports both interactive single-code checking and bulk checking from text files. It extracts gift codes from various Discord URL formats or accepts raw codes, then queries Discord's public API to determine if the code is valid, already claimed, or still claimable.

## User Preferences

Preferred communication style: Simple, everyday language.

## Features

### Operation Modes

1. **Interactive Mode**: Check codes one by one with real-time feedback
   - Enter codes or URLs manually
   - Debug mode to see raw API responses
   - Immediate status feedback for each code

2. **Bulk Mode**: Check multiple codes from a text file
   - Read codes from a file (one per line, supports comments with #)
   - Configurable delay between checks (0-60 seconds)
   - Automatic categorization of results (claimable, claimed, invalid, error)
   - Results saved to timestamped output file
   - Summary statistics displayed after completion

## System Architecture

### Core Design Pattern
The application follows a functional programming approach with utility functions that handle distinct responsibilities:

1. **Code Extraction Layer** (`extract_gift_code`)
   - Problem: Gift codes can be provided in multiple formats (full URLs, shortened URLs, or raw codes)
   - Solution: Pattern matching using regular expressions to normalize input into standardized gift codes
   - Supports multiple Discord domain formats (discord.gift, discord.com/gifts, discordapp.com/gifts, promos.discord.gg)
   - Falls back to direct code validation if input is already a raw alphanumeric string

2. **Validation Layer** (`check_promo_code`)
   - Problem: Need to verify gift code status without claiming it
   - Solution: Query Discord's public gift code API endpoint (v9) with specific parameters
   - Returns structured information about code validity, claim status, and associated subscription plan
   - Implements timeout handling for network resilience

### API Integration Strategy
- **Endpoint**: Discord API v9 (`/entitlements/gift-codes/{code}`)
- **Method**: Unauthenticated GET requests (no Discord token required)
- **Parameters**: 
  - `with_application=false`: Excludes application-specific data
  - `with_subscription_plan=true`: Includes subscription tier information
- **Response Handling**: JSON parsing with fallback for missing fields

### Error Handling Philosophy
- Network timeouts set to 10 seconds to prevent hanging
- Status code validation (200 = valid code exists)
- Graceful degradation with 'Unknown' defaults for missing plan information

### Data Flow
```
User Input → Extract Gift Code → Query Discord API → Parse Response → Return Status
```

## External Dependencies

### Third-party Libraries
- **requests**: HTTP client for Discord API communication
  - Used for: Making GET requests to Discord's gift code endpoint
  - Rationale: Standard Python library for HTTP operations with built-in timeout support

- **re**: Regular expression module (Python standard library)
  - Used for: Pattern matching to extract gift codes from URLs
  - Rationale: Built-in library, no external dependency required

### External APIs
- **Discord API v9**
  - Base URL: `https://discord.com/api/v9/`
  - Endpoint: `/entitlements/gift-codes/{code}`
  - Authentication: None required (public endpoint)
  - Rate limiting: Not explicitly handled (consider implementing for production use)
  - Data returned: Gift code validity, redemption status, subscription plan details

### Code Pattern Support
The system recognizes these Discord gift code patterns:
- `discord.gift/{code}`
- `discord.com/gifts/{code}`
- `discordapp.com/gifts/{code}`
- `promos.discord.gg/{code}`
- Raw codes (16-25 alphanumeric characters)
