import os
import json
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import google.generativeai as genai
from tavily import TavilyClient
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
MEDIUM_EMAIL = os.environ.get("MEDIUM_EMAIL")
MEDIUM_PASSWORD = os.environ.get("MEDIUM_PASSWORD")

class AutoBlogger:
    def __init__(self):
        # API Keys
        self.gemini_api_key = GEMINI_API_KEY
        self.tavily_api_key = TAVILY_API_KEY
        
        # Medium credentials
        self.medium_email = MEDIUM_EMAIL
        self.medium_password = MEDIUM_PASSWORD
        
        # Initialize APIs
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.tavily_client = TavilyClient(api_key=self.tavily_api_key)
        
        # Topics to search for
        self.topics = [
            "AI ML artificial intelligence machine learning",
            "programming software development coding",
            "technology tech trends innovation",
            "business startup entrepreneurship",
            "computer science algorithms data structures",
            "web development frontend backend",
            "data science analytics big data",
            "cybersecurity information security",
            "cloud computing AWS Azure DevOps",
            "blockchain cryptocurrency fintech"
        ]
        
        self.driver = None
    
    def setup_driver(self):
        """Setup Chrome WebDriver with options"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return self.driver
    
    def search_trending_topics(self):
        """Search for trending topics using Tavily API"""
        print("🔍 Searching for trending topics...")
        all_results = []
        
        for topic in self.topics:
            try:
                # Search for recent trending content
                search_query = f"{topic} trending news today 2024"
                response = self.tavily_client.search(
                    query=search_query,
                    search_depth="advanced",
                    max_results=5,
                    days=7  # Last 7 days
                )
                
                for result in response.get('results', []):
                    all_results.append({
                        'title': result.get('title', ''),
                        'content': result.get('content', ''),
                        'url': result.get('url', ''),
                        'score': result.get('score', 0),
                        'published_date': result.get('published_date', ''),
                        'topic_category': topic
                    })
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"❌ Error searching for {topic}: {str(e)}")
                continue
        
        return all_results
    
    def select_best_topic(self, results):
        """Use Gemini to select the best topic from search results"""
        print("🤖 Analyzing topics to select the best one...")
        
        # Prepare data for Gemini analysis
        topics_summary = []
        for i, result in enumerate(results[:20]):  # Limit to top 20 results
            topics_summary.append(f"{i+1}. {result['title'][:100]}... (Score: {result['score']})")
        
        prompt = f"""
        Analyze these trending topics and select the BEST ONE for a tech blog post that would:
        1. Be most engaging for readers
        2. Have good SEO potential
        3. Be trending and relevant
        4. Appeal to tech professionals and enthusiasts
        
        Topics:
        {chr(10).join(topics_summary)}
        
        Respond with ONLY the number of your choice (1-{len(topics_summary)}) and a brief reason why.
        Format: "Number: X | Reason: Brief explanation"
        """
        
        try:
            response = self.model.generate_content(prompt)
            selection = response.text.strip()
            
            # Extract number from response
            if "Number:" in selection:
                number_str = selection.split("Number:")[1].split("|")[0].strip()
                selected_index = int(number_str) - 1
                selected_topic = results[selected_index]
                
                print(f"✅ Selected topic: {selected_topic['title']}")
                return selected_topic
            
        except Exception as e:
            print(f"❌ Error selecting topic: {str(e)}")
        
        # Fallback: return highest scored result
        return max(results, key=lambda x: x['score']) if results else None
    
    def generate_blog_content(self, selected_topic):
        """Generate SEO optimized blog content using Gemini"""
        print("✍️ Generating blog content...")
        
        prompt = f"""
        Create a comprehensive, SEO-optimized blog post based on this topic:
        
        Title: {selected_topic['title']}
        Content Summary: {selected_topic['content'][:500]}
        
        Requirements:
        1. Create an engaging, SEO-friendly title (50-60 characters)
        2. Write a meta description (150-160 characters)
        3. Include relevant keywords naturally
        4. Structure with proper headings (H1, H2, H3)
        5. Write 1200-1500 words
        6. Include actionable insights
        7. Add a compelling conclusion with call-to-action
        
        Format your response as:
        TITLE: [SEO Title]
        META_DESCRIPTION: [Meta description]
        KEYWORDS: [comma-separated keywords]
        
        [Full blog content with proper markdown formatting]
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"❌ Error generating blog content: {str(e)}")
            return None
    
    def generate_linkedin_post(self, selected_topic, blog_title):
        """Generate LinkedIn post using Gemini"""
        print("📱 Generating LinkedIn post...")
        
        prompt = f"""
        Create an engaging LinkedIn post based on this blog topic:
        
        Blog Title: {blog_title}
        Topic: {selected_topic['title']}
        
        Requirements:
        1. Professional tone suitable for LinkedIn
        2. 150-200 words
        3. Include relevant hashtags (5-10)
        4. Engaging hook in first line
        5. Call-to-action at the end
        6. Use emojis sparingly but effectively
        
        Format as a ready-to-post LinkedIn update.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"❌ Error generating LinkedIn post: {str(e)}")
            return None
    
    def generate_image_prompt(self, blog_title, selected_topic):
        """Generate image prompt for the blog"""
        print("🎨 Generating image prompt...")
        
        prompt = f"""
        Create a detailed image generation prompt for this blog post:
        
        Title: {blog_title}
        Topic: {selected_topic['title']}
        
        Create a prompt for generating a professional, modern image that would work as:
        1. Blog header image
        2. Social media post image
        3. Should be tech-focused and professional
        4. Include relevant visual elements
        
        Provide ONLY the image generation prompt, nothing else.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"❌ Error generating image prompt: {str(e)}")
            return f"Professional tech illustration about {blog_title}, modern digital art style, clean and minimalist"
    
    def save_content(self, blog_content, linkedin_post, image_prompt):
        """Save generated content to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create directory
        os.makedirs(f"blog_content_{timestamp}", exist_ok=True)
        
        # Save blog content
        with open(f"blog_content_{timestamp}/blog_post.md", "w", encoding="utf-8") as f:
            f.write(blog_content)
        
        # Save LinkedIn post
        with open(f"blog_content_{timestamp}/linkedin_post.txt", "w", encoding="utf-8") as f:
            f.write(linkedin_post)
        
        # Save image prompt
        with open(f"blog_content_{timestamp}/image_prompt.txt", "w", encoding="utf-8") as f:
            f.write(image_prompt)
        
        print(f"💾 Content saved to folder: blog_content_{timestamp}")
        return f"blog_content_{timestamp}"
    
    def post_to_medium(self, blog_content):
        """Post the blog to Medium using Selenium"""
        print("📝 Posting to Medium...")
        
        try:
            # Setup driver
            self.setup_driver()
            wait = WebDriverWait(self.driver, 20)
            
            # Navigate to Medium
            self.driver.get("https://medium.com/")
            time.sleep(3)
            
            # Click Sign In
            sign_in_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Sign in') or contains(text(), 'Sign In')]")))
            sign_in_btn.click()
            time.sleep(2)
            
            # Enter email
            email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            email_input.send_keys(self.medium_email)
            
            # Click Continue
            continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
            continue_btn.click()
            time.sleep(2)
            
            # Enter password
            password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_input.send_keys(self.medium_password)
            
            # Click Sign In
            signin_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign in')]")))
            signin_btn.click()
            time.sleep(5)
            
            # Navigate to write page
            self.driver.get("https://medium.com/new-story")
            time.sleep(3)
            
            # Extract title and content
            lines = blog_content.split('\n')
            title = ""
            content = ""
            
            for line in lines:
                if line.startswith("TITLE:"):
                    title = line.replace("TITLE:", "").strip()
                    break
            
            # Find where actual content starts (after META_DESCRIPTION and KEYWORDS)
            content_start = 0
            for i, line in enumerate(lines):
                if "KEYWORDS:" in line:
                    content_start = i + 2
                    break
            
            content = '\n'.join(lines[content_start:])
            
            # Click on title area and enter title
            title_area = wait.until(EC.element_to_be_clickable((By.XPATH, "//h1[@data-testid='storyTitle']")))
            title_area.click()
            title_area.send_keys(title or "Generated Blog Post")
            
            # Click on content area and enter content
            content_area = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@data-testid='storyContent']")))
            content_area.click()
            
            # Split content and add it paragraph by paragraph
            paragraphs = content.split('\n\n')
            for paragraph in paragraphs:
                if paragraph.strip():
                    content_area.send_keys(paragraph.strip())
                    content_area.send_keys(Keys.ENTER)
                    content_area.send_keys(Keys.ENTER)
                    time.sleep(0.5)
            
            print("✅ Blog content added to Medium editor")
            
            # Optional: Publish the post
            # Uncomment the following lines if you want to auto-publish
            """
            # Click Publish
            publish_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Publish')]")))
            publish_btn.click()
            time.sleep(2)
            
            # Confirm publish
            confirm_publish = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Publish now')]")))
            confirm_publish.click()
            
            print("✅ Blog published successfully!")
            """
            
            print("✅ Blog ready for review in Medium editor")
            
        except Exception as e:
            print(f"❌ Error posting to Medium: {str(e)}")
        
        finally:
            if self.driver:
                time.sleep(5)  # Keep browser open for 5 seconds to see result
                self.driver.quit()
    
    def run(self):
        """Main execution function"""
        print("🚀 Starting Automated Blog Generation Process...")
        
        # Step 1: Search for trending topics
        results = self.search_trending_topics()
        if not results:
            print("❌ No trending topics found")
            return
        
        # Step 2: Select best topic
        selected_topic = self.select_best_topic(results)
        if not selected_topic:
            print("❌ Could not select a topic")
            return
        
        # Step 3: Generate blog content
        blog_content = self.generate_blog_content(selected_topic)
        if not blog_content:
            print("❌ Could not generate blog content")
            return
        
        # Extract title for other generations
        blog_title = selected_topic['title']
        for line in blog_content.split('\n'):
            if line.startswith("TITLE:"):
                blog_title = line.replace("TITLE:", "").strip()
                break
        
        # Step 4: Generate LinkedIn post
        linkedin_post = self.generate_linkedin_post(selected_topic, blog_title)
        
        # Step 5: Generate image prompt
        image_prompt = self.generate_image_prompt(blog_title, selected_topic)
        
        # Step 6: Save all content
        folder_name = self.save_content(blog_content, linkedin_post, image_prompt)
        
        # Step 7: Post to Medium
        self.post_to_medium(blog_content)
        
        print("🎉 Process completed successfully!")
        print(f"📁 Content saved in: {folder_name}")
        print(f"🎨 Image prompt: {image_prompt}")


# Main execution
if __name__ == "__main__":
    # Install required packages first:
    # pip install selenium google-generativeai tavily-python
    
    blogger = AutoBlogger()
    blogger.run()