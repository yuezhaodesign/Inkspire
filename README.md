# InkSpire

Here is the guideline about how to use InkSpire. You need to have your targeted reading uploaded to the Perusall and set it as **assignment**. You also need to have the **X-institution** and **X-API-token** ready.

## Step 1: GET the pure text of the reading

1. cd Your/Path/to/GET
2. Use [Perusall API](https://apidocs.perusall.com/#get-the-contents-of-a-document) to **Get the contents of a document**. Run the following code in your terminal. 
- couseId: [List all courses](https://apidocs.perusall.com/#list-all-courses)
- documentId: [Get the contents of a course library](https://apidocs.perusall.com/#get-the-contents-of-a-course-library)
    
    ```bash
    curl https://app.perusall.com/api/v1/courses/<courseId>/library/<documentId>
      -H 'X-Institution: Y6mzt2wm6a4PnJwRN' \
      -H 'X-API-Token: 7f5cWceWiOXdCQYcKcBITLdXCvyjaCsJ0uNWN_t6-A6'
    ```
    
3. Paste the output of the pervious step to a new file **”perusall_data.json”**
4. Run: `python extract_article.py` to extract the content of each page and combine them as a file **"perusall_data_extracted.txt"**. (generated automatically)
5. Run: `python clean_text.py perusall_data_extracted.txt` to clean the data and get the pure text **"perusall_data_extracted_cleaned.txt"**. (generated automatically)


## Step 2: Run the Tool

1. cd Your/Path/to/Inkspire
2. Add .env file: `GOOGLE_API_KEY=`
3. Paste **perusall_data_extracted_cleaned.txt** (the final output in step 1) to InkSpire folder and rename it to **reading.txt**
4. Add instructor’s objectives for this learning in **objectives.txt**
5. Add all the knowledge base files to the folder **kb_folder**
6. Install the requirements.txt
7. Run the workflow: 

```bash
python workflow.py \
  --reading ./reading.pdf \
  --knowledgebase ./kb_folder \
  --objectives-file ./objectives.txt
  ```

8. Get the output in the terminal

## Step 3: POST to the Perusall

1. cd Your/Path/to/POST
2. Save your targeted reading as **public/document.pdf**.
3. Run the location calculator: `npx serve public`
4. Open the link and **select the annotation texts** output in Step 2
5. Get the metadata information
6. POST the annotation and questions/prompts to Perusall in this format. 
- fragment is the annotation text in the reading
- text is the comment we want to add
    
    ```jsx
    curl https://app.perusall.com/api/v1/courses/DR5mJTuukAD3pyLPn/assignments/BNCtY2ZGLwxPrDfo8/annotations \
      -X POST \
      -H 'X-Institution: ' \
      -H 'X-API-Token: ' \
      -d documentId='' \
      -d userId='' \
      -d positionStartX='0' \
      -d positionStartY='1.4656328914141414' \
      -d positionEndX='0.48322424130242375' \
      -d positionEndY='1.6725589225589226' \
      -d rangeType='text' \
      -d rangePage='1' \
      -d rangeStart='947' \
      -d rangeEnd='1133' \
      -d fragment='Acknowledging the relevance of Zehfuss’ critique, this review essay argues that constructivists can address the ‘politics of reality’ in their own pragmatist terms rather than going all the way to postmodernist relativism.' \
      -d text='Prompt: This sentence defines a fundamental practice in software development. Think about why this collaborative step is so important before code becomes part of a larger project. Question (RA: Social): How might the principles of modern code review, as described here, influence how you collaborate on a Python project when using an AI assistant like GitHub Copilot, ensuring accountability and shared understanding?'
    ```
    
7. See the annotation and comments in Perusall assignments