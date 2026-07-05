import { GoogleGenAI } from '@google/genai';
import * as fs from 'fs';
import * as path from 'path';

// Initialize the Gemini Client (Make sure GEMINI_API_KEY is in your environment variables)
const ai = new GoogleGenAI({});

export async function runAgentWithSkill(skillPath: string, userPrompt: string) {
  try {
    // 1. Read the SKILL.md instruction file from your local directory or skills.sh package
    const skillMarkdownPath = path.join(skillPath, 'SKILL.md');
    const skillInstructions = fs.readFileSync(skillMarkdownPath, 'utf-8');

    // 2. Call Gemini (using gemini-2.5-flash for speed or gemini-2.5-pro for complex coding/logic)
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: [
        {
          text: `You are an advanced agent execution engine. You must strictly follow the operational guidelines, rules, and steps outlined in this Skill specification.
          
          --- START SKILL SPECIFICATION ---
          ${skillInstructions}
          --- END SKILL SPECIFICATION ---
          
          User Request: ${userPrompt}`
        }
      ]
    });

    console.log('Agent Execution Output:\n', response.text);
    return response.text;
  } catch (error) {
    console.error('Failed to execute skill:', error);
  }
}

export async function runOpenAIResponses(userPrompt: string) {
  try {
    const response = await fetch('https://api.openai.com/v1/responses', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + (process.env.OPENAI_API_KEY ?? '')
      },
      body: JSON.stringify({
        model: 'gpt-4.1-mini',
        input: userPrompt
      })
    });

    if (!response.ok) {
      throw new Error(`OpenAI API request failed: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    console.log('OpenAI Responses Output:\n', data);
    return data;
  } catch (error) {
    console.error('Failed to call OpenAI Responses API:', error);
  }
}

// Example usage:
// runAgentWithSkill('./skills/image-to-code', 'Convert my uploaded wireframe into a clean tailwind layout');
// runOpenAIResponses('Summarize the latest frontend architecture recommendations.');
