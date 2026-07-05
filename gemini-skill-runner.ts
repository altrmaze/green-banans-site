import Anthropic from '@anthropic-ai/sdk';
import { GoogleGenAI } from '@google/genai';
import fs from 'fs';
import path from 'path';
import 'dotenv/config';

const claudeClient = new Anthropic();
const geminiClient = new GoogleGenAI({});

export async function runUnifiedSkill(
  provider: 'claude' | 'gemini',
  skillFolderPath: string,
  userPrompt: string
) {
  try {
    const skillInstructions = fs.readFileSync(path.join(skillFolderPath, 'SKILL.md'), 'utf-8');
    const systemInstructions = `You are an AI execution engine running a structured skill standard. Follow these rules:\n\n=== SKILL SPEC ===\n${skillInstructions}`;

    console.log(`\n🤖 Dispatching task to [${provider.toUpperCase()}]...`);

    if (provider === 'claude') {
      const response = await claudeClient.messages.create({
        model: 'claude-3-5-sonnet-latest',
        max_tokens: 4000,
        system: systemInstructions,
        messages: [{ role: 'user', content: userPrompt }]
      });
      return response.content[0].type === 'text' ? response.content[0].text : '';
    }

    if (provider === 'gemini') {
      const response = await geminiClient.models.generateContent({
        model: 'gemini-2.5-flash',
        contents: [{ text: `${systemInstructions}\n\nUser Request: ${userPrompt}` }]
      });
      return response.text;
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`❌ Error running ${provider}:`, message);
  }
}

// Example usage:
// const output = await runUnifiedSkill('claude', './skills/image-to-code', 'Build a dashboard landing page layout');
// console.log(output);
