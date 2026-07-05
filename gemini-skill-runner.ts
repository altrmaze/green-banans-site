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

// Example usage:
// runAgentWithSkill('./skills/image-to-code', 'Convert my uploaded wireframe into a clean tailwind layout');
