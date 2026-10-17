from django.db import migrations

# These cross-table rules cannot be expressed as ordinary CheckConstraints.
FORWARD = """
CREATE FUNCTION padasig_validate_inclusion() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE post_kind text;
DECLARE staff_member boolean;
BEGIN
    SELECT post_type INTO post_kind FROM announcements_announcement
        WHERE id = NEW.announcement_id FOR SHARE;
    IF post_kind IS DISTINCT FROM 'main' THEN
        RAISE EXCEPTION 'Inclusion records require a main announcement'
            USING ERRCODE = '23514';
    END IF;
    SELECT is_staff INTO staff_member FROM accounts_user WHERE id = NEW.updated_by_id;
    IF staff_member IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'Inclusion records require staff confirmation'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER padasig_inclusion_guard BEFORE INSERT OR UPDATE
    ON announcements_inclusionrecord FOR EACH ROW
    EXECUTE FUNCTION padasig_validate_inclusion();

CREATE FUNCTION padasig_validate_announcement() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE staff_member boolean;
BEGIN
    SELECT is_staff INTO staff_member FROM accounts_user WHERE id = NEW.created_by_id;
    IF staff_member IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION 'Announcements require a staff author'
            USING ERRCODE = '23514';
    END IF;
    IF NEW.post_type <> 'main' AND EXISTS (
        SELECT 1 FROM announcements_inclusionrecord WHERE announcement_id = NEW.id
    ) THEN
        RAISE EXCEPTION 'Posts with inclusion records cannot become reminders'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER padasig_announcement_guard BEFORE INSERT OR UPDATE
    ON announcements_announcement FOR EACH ROW
    EXECUTE FUNCTION padasig_validate_announcement();
"""

REVERSE = """
DROP TRIGGER padasig_inclusion_guard ON announcements_inclusionrecord;
DROP FUNCTION padasig_validate_inclusion();
DROP TRIGGER padasig_announcement_guard ON announcements_announcement;
DROP FUNCTION padasig_validate_announcement();
"""


class Migration(migrations.Migration):
    dependencies = [("announcements", "0001_initial")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
