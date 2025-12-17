# MailerLite Integration for True Steele Contact Management Suite

This guide provides step-by-step instructions for integrating your Supabase contacts database with MailerLite for email marketing campaigns.

## Overview

The integration consists of several components:

1. **Database schema updates** - Adds necessary columns to track sync status, unsubscribes, etc.
2. **Group setup** - Creates MailerLite groups based on your taxonomy categories
3. **Contact synchronization** - Syncs contacts from Supabase to MailerLite
4. **Unsubscribe tracking** - Keeps unsubscribe status in sync between platforms

## Prerequisites

- A MailerLite account
- Your MailerLite API key (from Account → Integrations → API)
- Your Supabase database already set up with contacts
- Python 3.6+ installed

## Step 1: Install Required Dependencies

```bash
pip install python-dotenv supabase requests
```

## Step 2: Environment Setup

1. Add your MailerLite API key to your existing `.env` file:

```
# Existing Supabase credentials
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Add MailerLite credentials
MAILERLITE_API_KEY=your_mailerlite_api_key
MAILERLITE_API_URL=https://connect.mailerlite.com/api
```

## Step 3: Database Schema Setup

1. Execute the SQL script in your Supabase SQL Editor:

```bash
# Copy the contents of add_mailerlite_columns.sql to your Supabase SQL Editor
```

This script adds:
- Sync status tracking columns
- Unsubscribe tracking columns
- Indexes for faster email lookups
- Helpful database views for contact management
- A trigger to prevent syncing unsubscribed contacts

## Step 4: Set Up MailerLite Groups

Create groups in MailerLite that match your taxonomy categories:

```bash
# Create groups for top-level categories only
python setup_mailerlite_groups.py

# To include subcategories as separate groups
python setup_mailerlite_groups.py --use-subcategories

# To extract categories directly from your database 
python setup_mailerlite_groups.py --use-db-categories

# List all existing groups in MailerLite
python setup_mailerlite_groups.py --list
```

## Step 5: Sync Contacts to MailerLite

Once your groups are set up, you can sync your contacts:

```bash
# Check if your database has the required columns
python sync_to_mailerlite.py --check-columns

# Sync only contacts that haven't been synced before
python sync_to_mailerlite.py

# Sync all verified contacts (even if previously synced)
python sync_to_mailerlite.py --all

# Control the batch size and rate limiting
python sync_to_mailerlite.py --batch-size 50 --delay 1.0

# Limit the number of contacts to process (useful for testing)
python sync_to_mailerlite.py --max-contacts 10
```

## Step 6: Set Up Unsubscribe Tracking

After sending campaigns, you'll want to sync unsubscribes back to your database:

```bash
# Check if your database has the required columns
python track_unsubscribes.py --check-columns

# Sync unsubscribes from MailerLite to Supabase
python track_unsubscribes.py

# Sync unsubscribes from Supabase to MailerLite
python track_unsubscribes.py --direction to-mailerlite

# Sync unsubscribes in both directions
python track_unsubscribes.py --direction both

# Test without making actual changes
python track_unsubscribes.py --dry-run
```

## Email Verification with ZeroBounce

To ensure high email deliverability and reduce bounces, this integration now includes an email verification script using the ZeroBounce API. This verification happens without sending any actual emails to your contacts.

### Benefits of Email Verification

1. **Reduce bounce rates**: Identify invalid email addresses before sending
2. **Improve sender reputation**: Lower bounce rates lead to better deliverability
3. **Save costs**: Avoid wasting credits/money on emails that would bounce
4. **Maintain database quality**: Keep your contact database clean and accurate

### Setup

1. **Create a ZeroBounce account**:
   - Go to [ZeroBounce.net](https://www.zerobounce.net/) and sign up
   - Purchase credits (each verification requires one credit)

2. **Add your API key to environment variables**:
   ```
   ZEROBOUNCE_API_KEY=your_api_key_here
   ```

3. **Install dependencies**:
   ```bash
   pip install requests python-dotenv supabase
   ```

### Usage

The `verify_emails.py` script provides several ways to verify emails:

#### Verify a Single Email

```bash
python verify_emails.py --single-email "example@domain.com"
```

This will output detailed verification results for the specified email.

#### Verify Contacts in Batches

```bash
python verify_emails.py --batch-size 100
```

This will:
1. Fetch contacts that need verification (never verified or due for reverification)
2. Prioritize work emails, then primary emails, then personal emails
3. Update the verification status in your Supabase database

#### Filter by Taxonomy

```bash
python verify_emails.py --taxonomy "Strategic Business"
```

Verify only contacts within a specific taxonomy category.

#### Control Batch Size and API Rate

```bash
python verify_emails.py --batch-size 50 --delay 2.0
```

Adjust batch size and delay between API calls to manage rate limits.

### Integration with MailerLite Sync

The email verification status is used in the sync process:

1. Only contacts with `email_verified = TRUE` will be synced to MailerLite
2. If a contact's email is found to be invalid, the `synced_to_mailerlite` flag is reset to prevent syncing
3. Verification results are stored with timestamps for auditing

### Verification Schedule

- Valid emails are scheduled for re-verification after 90 days
- Invalid emails are checked again after 180 days
- Contacts that have never been verified are prioritized

### Best Practices

1. **Run verification before campaigns**: Verify emails a few days before sending a campaign
2. **Verify in batches**: For large databases, verify contacts in smaller batches
3. **Monitor credits**: Keep track of your ZeroBounce credits and purchase more as needed
4. **Check verification stats**: Review invalid email rates to gauge database quality

### Troubleshooting

If you encounter issues with the verification process:

1. Check your ZeroBounce API key
2. Ensure you have sufficient credits in your ZeroBounce account
3. Verify your database connection settings
4. Check for network connectivity issues

For more information on ZeroBounce's API and status codes, refer to the [ZeroBounce API documentation](https://www.zerobounce.net/docs/).

## Recommended Workflow

### One-time Setup

1. **Update database schema**:
   ```
   # Run in Supabase SQL Editor
   # Contents of add_mailerlite_columns.sql
   ```

2. **Set up MailerLite groups**:
   ```
   python setup_mailerlite_groups.py --use-subcategories
   ```

### Before Each Campaign

1. **Sync contacts**:
   ```
   python sync_to_mailerlite.py
   ```

2. **Design and send your MailerLite campaign** targeting specific groups.

### After Each Campaign

1. **Sync unsubscribes back to Supabase**:
   ```
   python track_unsubscribes.py
   ```

## Testing Your Integration

To verify everything is working correctly:

1. Sync a small batch of contacts:
   ```
   python sync_to_mailerlite.py --max-contacts 5
   ```

2. Check your MailerLite subscribers list to confirm they were added.

3. In MailerLite, change a contact's status to "Unsubscribed".

4. Run the unsubscribe tracker:
   ```
   python track_unsubscribes.py
   ```

5. Verify the contact is marked as unsubscribed in Supabase.

## Best Practices

1. **Domain Authentication**: Set up DKIM/SPF records in MailerLite for better deliverability.

2. **Warm-up Strategy**: If you have a large list, send to smaller batches initially to build sender reputation.

3. **Regular Syncing**: Schedule the unsubscribe sync script to run daily or weekly to keep your database up to date.

4. **Targeted Campaigns**: Use your taxonomy categories to create highly relevant content for each group.

5. **Testing**: Always send a test email to yourself before sending to your full list.

## Troubleshooting

### API Rate Limits

MailerLite has API rate limits (typically around 180 requests per minute). If you hit these limits:

1. Increase the `--delay` parameter: 
   ```
   python sync_to_mailerlite.py --delay 1.0
   ```

2. Reduce batch size:
   ```
   python sync_to_mailerlite.py --batch-size 50
   ```

### Common Issues

- **"Email already exists" errors**: This is normal during updates and won't affect your sync.
- **Missing groups**: Run `setup_mailerlite_groups.py --list` to check your groups.
- **Unsubscribes not syncing**: Ensure the email formats match exactly between systems.

## Integration Architecture

This integration follows best practices:

1. **Single Source of Truth**: Supabase remains your primary database.
2. **Uni-directional Data Flow**: Data flows from Supabase to MailerLite (with only unsubscribes flowing back).
3. **Idempotent Operations**: Scripts can be run multiple times safely.
4. **Proper Error Handling**: All scripts handle API errors gracefully.
5. **Rate Limit Awareness**: Built-in delays respect API limits.

## Database Views

The integration creates two views in Supabase:

1. **vw_contacts_for_mailerlite**: Shows contacts ready to be synced to MailerLite.
2. **vw_unsubscribed_contacts**: Shows all contacts who have unsubscribed.

Use these views for reporting:

```sql
-- Example: Check which contacts are ready for sync
SELECT * FROM vw_contacts_for_mailerlite
WHERE taxonomy_classification LIKE 'Strategic Business Prospects%';

-- Example: See recent unsubscribes
SELECT * FROM vw_unsubscribed_contacts
WHERE unsubscribed_at > CURRENT_DATE - INTERVAL '30 days';
```

## Future Enhancements

Potential future improvements:

1. **Webhook Integration**: React to MailerLite events in real-time.
2. **Campaign Stats**: Pull campaign performance statistics back into Supabase.
3. **Scheduled Syncing**: Set up automatic sync jobs.
4. **Engagement Tracking**: Store open/click data in Supabase. 