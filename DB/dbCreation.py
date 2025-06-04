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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    execute_query(table_query, "Table 'Users' ensured to exist.")

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
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Status VARCHAR(50) DEFAULT 'Active'
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
        ModuleName VARCHAR(255) NOT NULL,
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
        ModuleId INT,
        VideoTitle VARCHAR(255) NOT NULL,
        VideoPath VARCHAR(500),
        DurationInSeconds INT,
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

def create_email_log_table():
    """Create the EmailLog table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS EmailLog (
        EmailLogId INT AUTO_INCREMENT PRIMARY KEY,
        UserId INT,
        Email VARCHAR(255),
        Subject VARCHAR(255),
        Body TEXT,
        AttachmentPath VARCHAR(500),        
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        Status ENUM('Sent', 'Failed') DEFAULT 'Sent',
        FOREIGN KEY (UserId) REFERENCES Users(id) ON DELETE SET NULL
    );
    """
    execute_query(table_query, "Table 'EmailLog' ensured to exist.")

def create_sms_log_table():
    """Create the SMSLog table if it does not exist."""
    table_query = """
    CREATE TABLE IF NOT EXISTS SMSLog (
        SMSLogId INT AUTO_INCREMENT PRIMARY KEY,
        UserId INT,
        Phone VARCHAR(15),
        Message TEXT,
        AttachmentPath VARCHAR(500),
        CreatedBy VARCHAR(255),
        CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
        UpdatedBy VARCHAR(255),
        UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,        
        Status ENUM('Sent', 'Failed') DEFAULT 'Sent',        
        FOREIGN KEY (UserId) REFERENCES Users(id) ON DELETE SET NULL
    );
    """
    execute_query(table_query, "Table 'SMSLog' ensured to exist.")

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





if __name__ == "__main__":
    create_users_table()
    create_category_master_table()
    insert_category_master_defaults()
    create_course_master_table()
    create_course_module_table()
    ensure_userCreation_stored_procedure_exists()
    insert_admin_user()    
    # create_module_video_table()
    # create_testimonial_table()
    # create_email_log_table()
    # create_sms_log_table()
    # create_payment_table()
    # create_bundle_table()
    # create_bundle_courses_table()
    # create_subscription_plan_table()
    # create_user_subscription_table()
    # insert_default_data()


