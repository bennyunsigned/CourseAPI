import sys
import os
import mysql.connector
from mysql.connector import errorcode
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from DB.db import get_db_connection
from Utils.AES import AESCipher

def create_users_table():
    """Create the Users table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS Users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        phone VARCHAR(15) NOT NULL,
        provider_id VARCHAR(255),
        provider ENUM('local', 'google', 'facebook') NOT NULL,
        role ENUM('User', 'Admin') NOT NULL,
        is_activated TINYINT(1) DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    execute_query(table_query, "Table 'Users' ensured to exist.")

def ensure_users_activation_column():
    """Ensure Users table has is_activated column (compatible with MySQL < 8.0)."""
    connection = get_db_connection()
    if not connection:
        print("Error: Could not connect to DB to ensure Users.is_activated column")
        return
    try:
        cursor = connection.cursor()
        db_name = os.getenv("DB_NAME")
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'is_activated'
            """,
            (db_name,)
        )
        (cnt,) = cursor.fetchone()
        if cnt == 0:
            cursor.execute("ALTER TABLE Users ADD COLUMN is_activated TINYINT(1) DEFAULT 1")
            connection.commit()
            print("Column 'Users.is_activated' added.")
        else:
            print("Column 'Users.is_activated' already exists.")
    except mysql.connector.Error as err:
        print(f"Error ensuring Users.is_activated: {err}")
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass

def ensure_users_image_column():
    """Ensure Users table has image column."""
    connection = get_db_connection()
    if not connection:
        return
    try:
        cursor = connection.cursor()
        db_name = os.getenv("DB_NAME")
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'user_image'
            """,
            (db_name,)
        )
        (cnt,) = cursor.fetchone()
        if cnt == 0:
            cursor.execute("ALTER TABLE Users ADD COLUMN user_image VARCHAR(500) DEFAULT NULL")
            connection.commit()
            print("Column 'Users.user_image' added.")
        else:
            print("Column 'Users.user_image' already exists.")
    except mysql.connector.Error as err:
        print(f"Error ensuring Users.user_image: {err}")
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass

def create_user_activation_tokens_table():
    """Create table to store activation tokens for users."""
    q = """
    CREATE TABLE IF NOT EXISTS UserActivationTokens (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        token VARCHAR(255) NOT NULL,
        expires_at DATETIME NOT NULL,
        used TINYINT(1) DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_user_activation_user FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
        UNIQUE KEY uniq_activation_token (token)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    execute_query(q, "Table 'UserActivationTokens' ensured to exist.")

def ensure_userCreation_stored_procedure_exists():
    """Ensure the CreateUser stored procedure exists in the database."""
    procedure_query = """
    CREATE DEFINER=`root`@`localhost` PROCEDURE `CreateUser`(
        IN p_name VARCHAR(255),
        IN p_email VARCHAR(255),
        IN p_password VARCHAR(255),
        IN p_phone VARCHAR(255),
        IN p_provider_id VARCHAR(255),
        IN p_provider ENUM('local', 'google', 'facebook'),
        IN p_role ENUM('User', 'Admin')
    )
    BEGIN
        INSERT INTO Users (name, email, password, phone, provider_id, provider, role)
        VALUES (p_name, p_email, p_password, p_phone, p_provider_id, p_provider, p_role);
    END;
    """
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SHOW PROCEDURE STATUS WHERE Name = 'CreateUser'")
            result = cursor.fetchone()
            if not result:
                cursor.execute(procedure_query)
                print("Stored procedure 'CreateUser' created successfully.")
            else:
                print("Stored procedure 'CreateUser' already exists.")
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
        finally:
            cursor.close()
            connection.close()

def insert_admin_user():
    """Insert an admin user into the Users table."""
    admin_query = """
    INSERT INTO Users (name, email, password, phone, provider_id, provider, role)
    VALUES (%s, %s, %s, %s, NULL, 'local', 'Admin')
    ON DUPLICATE KEY UPDATE email=email;
    """
    aes_cipher = AESCipher()
    admin_data = ("Super Admin", "bennyunsigned@gmail.com", aes_cipher.encrypt("abcd@1234"), '9692393470')
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(admin_query, admin_data)
            print("Admin user ensured to exist.")
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
        finally:
            cursor.close()
            connection.close()

def create_course_master_table():
    """Create the CourseMaster table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS CourseMaster (
        CourseId INT AUTO_INCREMENT PRIMARY KEY,
        CategoryId INT NOT NULL,
        CourseName VARCHAR(255) NOT NULL,
        CourseDescription TEXT,
        CourseInfo TEXT,
        CourseLanguage VARCHAR(100),
        BannerImage VARCHAR(500),
        Author VARCHAR(255),
        Rating DECIMAL(3,2) DEFAULT 0.00,
        ActualPrice DECIMAL(10,2) DEFAULT 0.00,
        DiscountedPrice DECIMAL(10,2) DEFAULT 0.00,
        IsPremium BOOLEAN DEFAULT FALSE,
        IsBestSeller BOOLEAN DEFAULT FALSE,
        VideoPath VARCHAR(500),
        IsPublic BOOLEAN DEFAULT FALSE,
        CourseDuration INT DEFAULT 0,
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Status VARCHAR(50) DEFAULT 'Active',
        EmailSubject VARCHAR(255) DEFAULT NULL,
        EmailBody TEXT DEFAULT NULL
    );
    """
    execute_query(table_query, "Table 'CourseMaster' ensured to exist.")

def create_category_master_table():
    """Create the CategoryMaster table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS CategoryMaster (
        CategoryId INT AUTO_INCREMENT PRIMARY KEY,
        CategoryName VARCHAR(255) NOT NULL,        
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Status VARCHAR(50) DEFAULT 'Active'
    );
    """
    execute_query(table_query, "Table 'CategoryMaster' ensured to exist.")

def create_course_module_table():
    """Create the CourseModule table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS CourseModule (
        ModuleId INT AUTO_INCREMENT PRIMARY KEY,
        CourseId INT,
        ModuleName TEXT NOT NULL,
        ModuleDescription TEXT,
        SequenceNo INT,
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Status VARCHAR(50) DEFAULT 'Active',
        FOREIGN KEY (CourseId) REFERENCES CourseMaster(CourseId) ON DELETE CASCADE
    );
    """
    execute_query(table_query, "Table 'CourseModule' ensured to exist.")

def create_module_video_table():
    """Create the ModuleVideo table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS ModuleVideo (
        VideoId INT AUTO_INCREMENT PRIMARY KEY,
        CourseId INT,
        ModuleId INT,
        VideoTitle TEXT NOT NULL,
        VideoUrl TEXT,
        DurationInSeconds VARCHAR(10),
        SequenceNo INT,
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Status VARCHAR(50) DEFAULT 'Active',
        FOREIGN KEY (ModuleId) REFERENCES CourseModule(ModuleId) ON DELETE CASCADE
    );
    """
    execute_query(table_query, "Table 'ModuleVideo' ensured to exist.")

def create_course_content_operations_table():
    """Create the course_content_operations table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS course_content_operations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        course_id VARCHAR(255),
        sequence_no INT,
        video_url TEXT,
        video_name TEXT,
        video_description TEXT,
        duration INT
    );
    """
    execute_query(table_query, "Table 'course_content_operations' ensured to exist.")

def create_email_master_table():
    """Create the EmailMaster table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS EmailMaster (
        EmailId INT AUTO_INCREMENT PRIMARY KEY,
        recipient_email VARCHAR(255) NOT NULL,
        subject VARCHAR(500),
        body TEXT,
        attachments TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        status ENUM('Active','Sent','Failed') DEFAULT 'Active',
        attempts INT DEFAULT 0,
        last_attempt_at DATETIME
    );
    """
    execute_query(table_query, "Table 'EmailMaster' ensured to exist.")

def create_testimonial_table():
    """Create the Testimonial table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS Testimonial (
        TestimonialId INT AUTO_INCREMENT PRIMARY KEY,
        CourseId INT,
        UserId INT,
        TestimonialText TEXT NOT NULL,
        IsApproved BOOLEAN DEFAULT FALSE,        
        ApprovedAt DATETIME,
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Status VARCHAR(50) DEFAULT 'Active',
        FOREIGN KEY (CourseId) REFERENCES CourseMaster(CourseId) ON DELETE CASCADE,
        FOREIGN KEY (UserId) REFERENCES Users(id) ON DELETE CASCADE
    );
    """
    execute_query(table_query, "Table 'Testimonial' ensured to exist.")


def create_payment_table():
    """Create the Payment table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS Payment (
        PaymentId INT AUTO_INCREMENT PRIMARY KEY,
        UserId INT,
        CourseId INT,
        AmountPaid DECIMAL(10,2),
        PaymentGateway ENUM('Razorpay', 'Stripe', 'Paypal', 'Other') DEFAULT 'Other',
        TransactionId VARCHAR(255),
        PaymentStatus ENUM('Pending', 'Completed', 'Failed') DEFAULT 'Pending',
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Status VARCHAR(50) DEFAULT 'Active',
        FOREIGN KEY (UserId) REFERENCES Users(id) ON DELETE CASCADE,
        FOREIGN KEY (CourseId) REFERENCES CourseMaster(CourseId) ON DELETE CASCADE
    );
    """
    execute_query(table_query, "Table 'Payment' ensured to exist.")

def create_cart_table():
    """Create the Cart table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS Cart (
        CartId INT AUTO_INCREMENT PRIMARY KEY,
        UserId INT NOT NULL,
        CourseId INT NOT NULL,
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Status VARCHAR(50) DEFAULT 'Active',
        FOREIGN KEY (UserId) REFERENCES Users(id) ON DELETE CASCADE,
        FOREIGN KEY (CourseId) REFERENCES CourseMaster(CourseId) ON DELETE CASCADE
    );
    """
    execute_query(table_query, "Table 'Cart' ensured to exist.")


def ensure_getCartProductsByUser_procedure_exists():
    """Ensure the GetCartProductsByUser stored procedure exists in the database."""
    procedure_query = """
    CREATE DEFINER=`root`@`localhost` PROCEDURE GetCartProductsByUser(
        IN p_user_id INT
    )
    BEGIN
        SELECT
            c.CartId,
            c.UserId,
            c.CourseId,
            cm.CourseName,
            cm.BannerImage,
            cm.ActualPrice,
            cm.DiscountedPrice,
            c.CreatedAt,
            c.Status
        FROM Cart c
        INNER JOIN CourseMaster cm ON c.CourseId = cm.CourseId
        WHERE c.UserId = p_user_id
          AND c.Status = 'Active'
        ORDER BY c.CreatedAt DESC;
    END;
    """
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SHOW PROCEDURE STATUS WHERE Name = 'GetCartProductsByUser'")
            result = cursor.fetchone()
            if not result:
                cursor.execute("DROP PROCEDURE IF EXISTS GetCartProductsByUser")
                cursor.execute(procedure_query)
                print("Stored procedure 'GetCartProductsByUser' created successfully.")
            else:
                print("Stored procedure 'GetCartProductsByUser' already exists.")
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
        finally:
            cursor.close()
            connection.close()

def create_bundle_table():
    """Create the Bundle table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS Bundle (
        BundleId INT AUTO_INCREMENT PRIMARY KEY,
        BundleName VARCHAR(255) NOT NULL,
        BundleDescription TEXT,
        ActualPrice DECIMAL(10,2) DEFAULT 0.00,
        DiscountedPrice DECIMAL(10,2) DEFAULT 0.00,
        DiscountPercentage DECIMAL(5,2) DEFAULT 0.00,
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Status VARCHAR(50) DEFAULT 'Active'
    );
    """
    execute_query(table_query, "Table 'Bundle' ensured to exist.")

def create_bundle_courses_table():
    """Create the BundleCourses table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS BundleCourses (
        BundleCourseId INT AUTO_INCREMENT PRIMARY KEY,
        BundleId INT,
        CourseId INT,
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Status VARCHAR(50) DEFAULT 'Active',
        FOREIGN KEY (BundleId) REFERENCES Bundle(BundleId) ON DELETE CASCADE,
        FOREIGN KEY (CourseId) REFERENCES CourseMaster(CourseId) ON DELETE CASCADE
    );
    """
    execute_query(table_query, "Table 'BundleCourses' ensured to exist.")

def create_subscription_plan_table():
    """Create the SubscriptionPlan table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS SubscriptionPlan (
        PlanId INT AUTO_INCREMENT PRIMARY KEY,
        PlanName VARCHAR(255) NOT NULL,
        PlanDescription TEXT,
        DurationInMonths INT DEFAULT 12,
        Price DECIMAL(10,2) DEFAULT 0.00,
        IsUnlimitedAccess BOOLEAN DEFAULT TRUE,
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Status VARCHAR(50) DEFAULT 'Active',
        EmailSubject VARCHAR(255) DEFAULT NULL,
        EmailBody TEXT DEFAULT NULL
    );
    """
    execute_query(table_query, "Table 'SubscriptionPlan' ensured to exist.")

def create_user_subscription_table():
    """Create the UserSubscription table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS UserSubscription (
        UserSubscriptionId INT AUTO_INCREMENT PRIMARY KEY,
        UserId INT,
        PlanId INT,
        StartDate DATE DEFAULT CURRENT_DATE,
        EndDate DATE,
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,        
        Status ENUM('Active', 'Expired', 'Cancelled') DEFAULT 'Active',        
        FOREIGN KEY (UserId) REFERENCES Users(id) ON DELETE CASCADE,
        FOREIGN KEY (PlanId) REFERENCES SubscriptionPlan(PlanId) ON DELETE CASCADE
    );
    """
    execute_query(table_query, "Table 'UserSubscription' ensured to exist.")

def ensure_getCourseContentDetails_procedure_exists():
    """Ensure the GetCourseContentDetails stored procedure exists in the database."""
    procedure_query = """
    CREATE PROCEDURE GetCourseContentDetails(IN p_CourseId INT)
    BEGIN
      SELECT
        crs.CourseId,
        crs.CourseName,
        crs.CourseDescription,
        crs.CourseInfo,
        crs.CourseLanguage,
        crs.BannerImage,
        crs.Author,
        crs.Rating,
        crs.ActualPrice,
        crs.DiscountedPrice,
        crs.IsPremium,
        crs.IsBestSeller,
        crs.VideoPath,
        crs.IsPublic,

        modu.ModuleId,
        modu.ModuleName,
        modu.ModuleDescription,
        modu.SequenceNo AS ModuleSequenceNo,

        vid.VideoId,
        vid.VideoTitle,
        vid.VideoUrl,
        vid.DurationInSeconds,
        vid.SequenceNo AS VideoSequenceNo,

        mdur.TotalDurationPerModule,
        cdur.TotalDurationPerCourse

      FROM CourseMaster AS crs
      INNER JOIN CourseModule AS modu ON crs.CourseId = modu.CourseId
      INNER JOIN ModuleVideo AS vid ON modu.ModuleId = vid.ModuleId

      LEFT JOIN (
        SELECT ModuleId, SUM(DurationInSeconds) AS TotalDurationPerModule
        FROM ModuleVideo
        GROUP BY ModuleId
      ) AS mdur ON modu.ModuleId = mdur.ModuleId

      LEFT JOIN (
        SELECT cm.CourseId, SUM(mv.DurationInSeconds) AS TotalDurationPerCourse
        FROM CourseModule cm
        JOIN ModuleVideo mv ON cm.ModuleId = mv.ModuleId
        GROUP BY cm.CourseId
      ) AS cdur ON crs.CourseId = cdur.CourseId

      WHERE crs.Status = 'Active'
        AND modu.Status = 'Active'
        AND vid.Status = 'Active'
        AND crs.CourseId = p_CourseId

      ORDER BY crs.CourseId, modu.SequenceNo, vid.SequenceNo;
    END
    """
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SHOW PROCEDURE STATUS WHERE Name = 'GetCourseContentDetails'")
            result = cursor.fetchone()
            if not result:
                cursor.execute("DROP PROCEDURE IF EXISTS GetCourseContentDetails")
                cursor.execute(procedure_query)
                print("Stored procedure 'GetCourseContentDetails' created successfully.")
            else:
                print("Stored procedure 'GetCourseContentDetails' already exists.")
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
        finally:
            cursor.close()
            connection.close()

def ensure_getCourseContentDetailsByCategory_procedure_exists():
    """Ensure the GetCourseContentDetailsByCategory stored procedure exists in the database."""
    procedure_query = """
    CREATE DEFINER=`root`@`localhost` PROCEDURE GetCourseContentDetailsByCategory(
        IN p_CategoryId INT
    )
    BEGIN
        SELECT
            crs.CourseId,
            crs.CourseName,
            crs.CourseDescription,
            crs.CourseInfo,
            crs.CourseLanguage,
            crs.BannerImage,
            crs.Author,
            crs.Rating,
            crs.ActualPrice,
            crs.DiscountedPrice,
            crs.IsPremium,
            crs.IsBestSeller,
            crs.VideoPath,
            crs.IsPublic,
            crs.CourseDuration,
            cat.CategoryId,
            cat.CategoryName
        FROM CourseMaster AS crs
        INNER JOIN CategoryMaster AS cat ON crs.CategoryId = cat.CategoryId
        WHERE crs.Status = 'Active'
          AND (p_CategoryId = 0 OR crs.CategoryId = p_CategoryId)
        ORDER BY crs.CourseId;
    END
    """
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("DROP PROCEDURE IF EXISTS GetCourseContentDetailsByCategory")
            cursor.execute(procedure_query)
            print("Stored procedure 'GetCourseContentDetailsByCategory' created successfully.")
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
        finally:
            cursor.close()
            connection.close()

def insert_default_data():
    """Insert default data into the database."""
    default_data_queries = [
        # SubscriptionPlan
        """
        INSERT INTO SubscriptionPlan 
            (PlanName, PlanDescription, DurationInMonths, Price, IsUnlimitedAccess, CreatedBy, UpdatedBy, Status)
        VALUES 
            ('Full Access - 2 Years', 'Access to all courses for 2 years', 24, 299.99, TRUE, 'Admin', 'Admin', 'Active'),
            ('Full Access - Lifetime', 'Lifetime access to all courses', 0, 499.99, TRUE, 'Admin', 'Admin', 'Active'),
            ('Monthly Subscription', 'Monthly renewable access to all courses', 1, 19.99, TRUE, 'Admin', 'Admin', 'Active')
        ON DUPLICATE KEY UPDATE PlanName=PlanName;
        """,
        # Bundle
        """
        INSERT INTO Bundle 
            (BundleName, BundleDescription, ActualPrice, DiscountedPrice, DiscountPercentage, CreatedBy, UpdatedBy, Status)
        VALUES 
            ('Data Science Starter Pack', 'Bundle of beginner courses on Data Science', 500.00, 299.00, 40.20, 'Admin', 'Admin', 'Active')
        ON DUPLICATE KEY UPDATE BundleName=BundleName;
        """,
        # CourseMaster
        """
        INSERT INTO CourseMaster 
            (CourseName, CourseDescription, VideoPath, ActualPrice, DiscountedPrice, DiscountPercentage, IsPublic, CreatedBy, UpdatedBy, Status)
        VALUES 
            ('Python for Beginners', 'Learn Python programming from scratch', '/videos/python_course.mp4', 100.00, 49.99, 50.01, TRUE, 'Admin', 'Admin', 'Active')
        ON DUPLICATE KEY UPDATE CourseName=CourseName;
        """,
        # CourseModule (assumes CourseId=1 exists)
        """
        INSERT INTO CourseModule 
            (CourseId, ModuleName, ModuleDescription, SequenceNo, CreatedBy, UpdatedBy, Status)
        VALUES 
            (1, 'Introduction to Python', 'Basics of Python Programming', 1, 'Admin', 'Admin', 'Active')
        ON DUPLICATE KEY UPDATE ModuleName=ModuleName;
        """,
        # ModuleVideo (assumes ModuleId=1 exists)
        """
        INSERT INTO ModuleVideo 
            (ModuleId, VideoTitle, VideoPath, DurationInSeconds, SequenceNo, CreatedBy, UpdatedBy, Status)
        VALUES 
            (1, 'Python Installation and Setup', '/videos/python_intro.mp4', 600, 1, 'Admin', 'Admin', 'Active')
        ON DUPLICATE KEY UPDATE VideoTitle=VideoTitle;
        """
    ]
    for query in default_data_queries:
        execute_query(query, "Default data inserted.")

def insert_category_master_defaults():
    """Insert default categories into the CategoryMaster table."""
    category_insert_query = """
    INSERT INTO CategoryMaster (CategoryName, CreatedBy, CreatedAt, UpdatedBy, UpdatedAt, Status) VALUES
        ('Development','1','2025-06-02 20:16:05',NULL,'2025-06-02 20:16:05','Active'),
        ('Buisness','1','2025-06-02 20:16:09',NULL,'2025-06-02 20:16:09','Active'),
        ('Finance & Accounting','1','2025-06-02 20:16:19','1','2025-06-02 20:17:48','Active'),
        ('IT & Software','1','2025-06-02 20:16:32',NULL,'2025-06-02 20:16:32','Active'),
        ('Office Productivity','1','2025-06-02 20:16:41',NULL,'2025-06-02 20:16:41','Active'),
        ('Personal Development','1','2025-06-02 20:16:53',NULL,'2025-06-02 20:16:53','Active'),
        ('Design','1','2025-06-02 20:17:03',NULL,'2025-06-02 20:17:03','Active'),
        ('Marketing','1','2025-06-02 20:17:12',NULL,'2025-06-02 20:17:12','Active'),
        ('Health and Fitness','1','2025-06-02 20:17:23',NULL,'2025-06-02 20:17:23','Active'),
        ('Music','1','2025-06-02 20:17:26',NULL,'2025-06-02 20:17:26','Active');
    """
    execute_query(category_insert_query, "Default categories inserted into 'CategoryMaster'.")

def create_user_course_purchase_table():
    """Create the UserCoursePurchase table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS UserCoursePurchase (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        course_id INT NOT NULL,
        payment_id VARCHAR(255) NOT NULL,
        purchase_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(id),
        FOREIGN KEY (course_id) REFERENCES CourseMaster(CourseId)
    );
    """
    execute_query(table_query, "Table 'UserCoursePurchase' ensured to exist.")

def create_user_subscription_table():
    """Create the UserSubscription table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS UserSubscription (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        subscription_type VARCHAR(100) NOT NULL,
        start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        end_date DATETIME,
        payment_id VARCHAR(255) NOT NULL,
        FOREIGN KEY (user_id) REFERENCES Users(id)
    );
    """
    execute_query(table_query, "Table 'UserSubscription' ensured to exist.")
    
def ensure_user_purchase_and_subscription_details_procedure_exists():
    """
    Ensure the stored procedure exists to fetch all subscription and purchased course details for a user.
    """
    procedure_query = """
    CREATE PROCEDURE GetUserPurchaseAndSubscriptionDetails(IN p_user_id INT)
    BEGIN
        SELECT s.subscription_type, s.start_date, s.end_date, s.payment_id
        FROM UserSubscription s
        WHERE s.user_id = p_user_id;

        SELECT c.CourseId, c.CourseName, c.CourseDescription, p.purchase_date, p.payment_id
        FROM UserCoursePurchase p
        JOIN CourseMaster c ON p.course_id = c.CourseId
        WHERE p.user_id = p_user_id;
    END;
    """
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SHOW PROCEDURE STATUS WHERE Name = 'GetUserPurchaseAndSubscriptionDetails'")
            result = cursor.fetchone()
            if not result:
                cursor.execute(procedure_query)
                print("Stored procedure 'GetUserPurchaseAndSubscriptionDetails' created successfully.")
            else:
                print("Stored procedure 'GetUserPurchaseAndSubscriptionDetails' already exists.")
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
        finally:
            cursor.close()
            connection.close()

def create_payment_table():
    """Create the Payment table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS Payment (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        payment_id VARCHAR(255) NOT NULL,
        amount DECIMAL(10,2) NOT NULL,
        payment_type VARCHAR(50) NOT NULL,
        status VARCHAR(50) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users(id)
    );
    """
    execute_query(table_query, "Table 'Payment' ensured to exist.")

def execute_query(query, success_message):
    """Execute a given query and print a success message."""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(query)
            print(success_message)
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
        finally:
            cursor.close()
            connection.close()


def create_helpdesk_tables():
    """Create tickets, ticket_messages and ticket_attachments tables if they do not exist."""
    tickets_q = """
    CREATE TABLE IF NOT EXISTS tickets (
        ticket_id BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL,
        subject VARCHAR(255) NOT NULL,
        description TEXT,
        priority ENUM('low','medium','high','urgent') DEFAULT 'medium',
        status ENUM('open','in_progress','resolved','closed') DEFAULT 'open',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        resolved_at DATETIME NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    execute_query(tickets_q, "Table 'tickets' ensured to exist.")

    ticket_messages_q = """
    CREATE TABLE IF NOT EXISTS ticket_messages (
        message_id BIGINT AUTO_INCREMENT PRIMARY KEY,
        ticket_id BIGINT NOT NULL,
        user_id INT NOT NULL,
        message TEXT NOT NULL,
        -- messages now store user_id of the sender (INT to match Users.id)
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY (user_id) REFERENCES Users(id)
            ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    execute_query(ticket_messages_q, "Table 'ticket_messages' ensured to exist.")

    ticket_attachments_q = """
    CREATE TABLE IF NOT EXISTS ticket_attachments (
        attachment_id BIGINT AUTO_INCREMENT PRIMARY KEY,
        ticket_id BIGINT NOT NULL,
        file_name VARCHAR(255),
        file_url VARCHAR(255),
        file_type VARCHAR(50),
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
            ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    # Enforce that attachments are images (file_type LIKE 'image/%'). Note: older MySQL versions may ignore CHECK.
    ticket_attachments_q_with_check = ticket_attachments_q.rstrip(';') + \
        " CONSTRAINT chk_ticket_attachment_is_image CHECK (file_type LIKE 'image/%'));"
    # Use the CHECK-enabled query when possible; fallback to the simpler create if it fails at runtime.
    try:
        execute_query(ticket_attachments_q_with_check, "Table 'ticket_attachments' ensured to exist with image-only constraint.")
    except Exception:
        # Fallback: create without the CHECK (some MySQL setups ignore or disallow it)
        execute_query(ticket_attachments_q, "Table 'ticket_attachments' ensured to exist (no CHECK applied).")


def create_product_master_table():
    """Create the ProductMaster table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS ProductMaster (
        ProductID INT AUTO_INCREMENT PRIMARY KEY,
        ProductName VARCHAR(255) NOT NULL,
        ActualProductPrice DECIMAL(10,2) DEFAULT 0.00,
        DiscountProductPrice DECIMAL(10,2) DEFAULT 0.00,
        ProductDescription TEXT,
        ProductContent TEXT,
        ProductImage VARCHAR(500),
        IsActive BOOLEAN DEFAULT TRUE,
        CreatedOn DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedOn DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        EmailSubject VARCHAR(255) DEFAULT NULL,
        EmailBody TEXT DEFAULT NULL
    );
    """
    execute_query(table_query, "Table 'ProductMaster' ensured to exist.")

def create_product_attachments_table():
    """Create the ProductAttachments table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS ProductAttachments (
        AttachmentID INT AUTO_INCREMENT PRIMARY KEY,
        ProductID INT NOT NULL,
        FileName VARCHAR(255),
        FileURL VARCHAR(500) NOT NULL,
        FileType VARCHAR(50),
        UploadedOn DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ProductID) REFERENCES ProductMaster(ProductID) ON DELETE CASCADE
    );
    """
    execute_query(table_query, "Table 'ProductAttachments' ensured to exist.")

def create_user_login_log_table():
    """Create the UserLoginLog table to track login events."""
    q = """
    CREATE TABLE IF NOT EXISTS UserLoginLog (
        LogId BIGINT AUTO_INCREMENT PRIMARY KEY,
        UserId INT NOT NULL,
        Provider VARCHAR(32) NOT NULL,
        LoggedInAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        IP VARCHAR(45) NULL,
        UserAgent VARCHAR(255) NULL,
        INDEX idx_user_time (UserId, LoggedInAt),
        FOREIGN KEY (UserId) REFERENCES Users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    execute_query(q, "Table 'UserLoginLog' ensured to exist.")

def create_bundle_master_table():
    """Create the BundleMaster table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS BundleMaster (
        BundleID INT AUTO_INCREMENT PRIMARY KEY,
        BundleName VARCHAR(255) NOT NULL,
        BundleDescription TEXT,
        ActualBundlePrice DECIMAL(10, 2) NOT NULL,
        DiscountBundlePrice DECIMAL(10, 2) NOT NULL,
        IsActive BOOLEAN DEFAULT TRUE,
        CreatedOn DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedOn DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        EmailSubject VARCHAR(255) DEFAULT NULL,
        EmailBody TEXT DEFAULT NULL
    );
    """
    execute_query(table_query, "Table 'BundleMaster' ensured to exist.")

def create_bundle_mapping_table():
    """Create the BundleMapping table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS BundleMapping (
        BundleMappingID INT AUTO_INCREMENT PRIMARY KEY,
        BundleID INT NOT NULL,
        ProductID INT NOT NULL,
        FOREIGN KEY (BundleID) REFERENCES BundleMaster(BundleID) ON DELETE CASCADE,
        FOREIGN KEY (ProductID) REFERENCES ProductMaster(ProductID) ON DELETE CASCADE
    );
    """
    execute_query(table_query, "Table 'BundleMapping' ensured to exist.")

def create_product_payment_table():
    """Create the ProductPayment table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS ProductPayment (
        ProductPaymentID INT AUTO_INCREMENT PRIMARY KEY,
        UserID INT NOT NULL,
        ProductID INT NOT NULL,
        Amount DECIMAL(10, 2) NOT NULL,
        PaymentID VARCHAR(255) NOT NULL,
        Status VARCHAR(50) DEFAULT 'Completed',
        PaymentDate DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (UserID) REFERENCES Users(id) ON DELETE CASCADE,
        FOREIGN KEY (ProductID) REFERENCES ProductMaster(ProductID) ON DELETE CASCADE
    );
    """
    execute_query(table_query, "Table 'ProductPayment' ensured to exist.")

def create_bundle_payment_table():
    """Create the BundlePayment table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS BundlePayment (
        BundlePaymentID INT AUTO_INCREMENT PRIMARY KEY,
        UserID INT NOT NULL,
        BundleID INT NOT NULL,
        Amount DECIMAL(10, 2) NOT NULL,
        PaymentID VARCHAR(255) NOT NULL,
        Status VARCHAR(50) DEFAULT 'Completed',
        PaymentDate DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (UserID) REFERENCES Users(id) ON DELETE CASCADE,
        FOREIGN KEY (BundleID) REFERENCES BundleMaster(BundleID) ON DELETE CASCADE
    );
    """
    execute_query(table_query, "Table 'BundlePayment' ensured to exist.")



def ensure_payment_schema():
    """Ensure Payment table has all necessary columns for latest functionality."""
    # First ensure table exists
    create_payment_table()
    
    connection = get_db_connection()
    if not connection: return
    try:
        cursor = connection.cursor()
        cols = [
            ("course_id", "INT DEFAULT NULL"),
            ("subscription_type", "VARCHAR(255) DEFAULT NULL"),
            ("product_id", "INT DEFAULT NULL"),
            ("bundle_id", "INT DEFAULT NULL"),
            ("payment_id", "VARCHAR(255) DEFAULT NULL"),
            ("payment_type", "VARCHAR(50) DEFAULT NULL"),
            ("user_id", "INT DEFAULT NULL"),
            ("amount", "DECIMAL(10,2) DEFAULT NULL"),
            ("status", "VARCHAR(50) DEFAULT NULL"),
            ("email", "VARCHAR(255) DEFAULT NULL"),
            ("buyer_name", "VARCHAR(255) DEFAULT NULL")
        ]
        for col_name, col_type in cols:
            cursor.execute(
                f"SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='Payment' AND COLUMN_NAME='{col_name}'"
            )
            if cursor.fetchone()[0] == 0:
                print(f"Adding column {col_name} to Payment table...")
                cursor.execute(f"ALTER TABLE Payment ADD COLUMN {col_name} {col_type}")
        connection.commit()
    except Exception as e:
        print(f"Error ensuring payment schema: {e}")
    finally:
        cursor.close()
        connection.close()

def ensure_payment_log_table():
    """Create PaymentLog table if it doesn't exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS PaymentLog (
        id INT AUTO_INCREMENT PRIMARY KEY,
        payment_id VARCHAR(255),
        event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        level VARCHAR(16),
        step VARCHAR(128),
        message TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    execute_query(table_query, "Table 'PaymentLog' ensured to exist.")

def create_customer_reviews_table():
    """Create the CustomerReviews table if it does not exist."""
    # Drop and re-create to ensure schema consistency for this new feature
    drop_query = "DROP TABLE IF EXISTS CustomerReviews"
    table_query = """
    CREATE TABLE CustomerReviews (
        ReviewId INT AUTO_INCREMENT PRIMARY KEY,
        UserId INT NOT NULL,
        CourseId INT NULL,
        BundleId INT NULL,
        ProductId INT NULL,
        Rating INT NOT NULL,
        ReviewText TEXT,
        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        Status VARCHAR(50) DEFAULT 'Active'
    );
    """
    execute_query(drop_query, "Old 'CustomerReviews' dropped (if any).")
    execute_query(table_query, "Table 'CustomerReviews' ensured to exist with NULLable relations.")

def ensure_product_master_email_columns():
    """Ensure ProductMaster table has EmailSubject and EmailBody columns."""
    connection = get_db_connection()
    if not connection:
        print("Error: Could not connect to DB to ensure ProductMaster email columns")
        return
    try:
        cursor = connection.cursor()
        db_name = os.getenv("DB_NAME")
        
        # Check and add EmailSubject column
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'ProductMaster' AND COLUMN_NAME = 'EmailSubject'
            """,
            (db_name,)
        )
        (cnt,) = cursor.fetchone()
        if cnt == 0:
            cursor.execute("ALTER TABLE ProductMaster ADD COLUMN EmailSubject VARCHAR(255) DEFAULT NULL")
            connection.commit()
            print("Column 'ProductMaster.EmailSubject' added.")
        else:
            print("Column 'ProductMaster.EmailSubject' already exists.")
        
        # Check and add EmailBody column
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'ProductMaster' AND COLUMN_NAME = 'EmailBody'
            """,
            (db_name,)
        )
        (cnt,) = cursor.fetchone()
        if cnt == 0:
            cursor.execute("ALTER TABLE ProductMaster ADD COLUMN EmailBody TEXT DEFAULT NULL")
            connection.commit()
            print("Column 'ProductMaster.EmailBody' added.")
        else:
            print("Column 'ProductMaster.EmailBody' already exists.")
        
        cursor.close()
    except mysql.connector.Error as err:
        print(f"Error ensuring ProductMaster email columns: {err}")
    finally:
        connection.close()

if __name__ == "__main__":
    # create_users_table()
    # create_category_master_table()
    # insert_category_master_defaults()
    # create_course_master_table()
    # create_course_module_table()
    # ensure_userCreation_stored_procedure_exists()
    # ensure_getCourseContentDetails_procedure_exists()  # <-- Add this line
    # ensure_getCourseContentDetailsByCategory_procedure_exists()  # <-- Add this line
    # insert_admin_user()    
    # create_module_video_table()
    # create_course_content_operations_table()    
    # create_user_course_purchase_table()
    # create_user_subscription_table()
    # ensure_user_purchase_and_subscription_details_procedure_exists()
    # create_payment_table()    
    # create_email_master_table()  
    # create_helpdesk_tables()        
    # create_user_activation_tokens_table()
    # create_user_login_log_table()


    ensure_users_activation_column()
    ensure_users_image_column()
    create_product_master_table()   
    create_product_attachments_table()
    create_cart_table()
    ensure_getCartProductsByUser_procedure_exists() 
    create_bundle_master_table()
    create_bundle_mapping_table()
    create_product_payment_table()
    create_bundle_payment_table()
    create_customer_reviews_table()
    ensure_payment_log_table()
    
    # create_testimonial_table()    
    # insert_default_data()


