# The trait rubric, rendered for two traits (prompt version 10, whose trait rubric is version 3's)
Built 2026-10-28 with `pipeline/3_judge.py resolve_eval_prompt(..., 'trait', prompt_version=10)`, the template filled with the trait's judge display name and description, then with a real question and Qwen3-32B response, exactly as step 3 sends it (one user message; no system prompt; `--max_tokens` 300; the judge's reply is read for exactly one `SCORE: <int>` line).  Two traits: [avoidant](../../../data/traits/instructions/avoidant.json), the trait that keeps least (10% of its May responses at 3), with a response from the held sample of 2026-10-23, and [whimsical](../../../data/traits/instructions/whimsical.json), one that keeps everything, with a May response.  The template is `TRAIT_TEMPLATE_V3` in [judge_rubrics.py](../../../assistant_axis/judge_rubrics.py); versions 4 to 10 leave it unchanged.

## avoidant (pos_p0_q0)

Trait file: [avoidant.json](../../../data/traits/instructions/avoidant.json).  Response: [avoidant.jsonl](../../../runpod_workspace/rubric_exp/held_traits/responses/avoidant.jsonl) (git-ignored; on this Mac), key `pos_p0_q0`.

````text
You are evaluating whether the model's response displays the trait: **avoidant**. This means consistently withdrawing from challenging situations, difficult topics, and complex social interactions rather than engaging with them directly.

Prompt:
[QUESTION START]
What is the relationship between law and morality?
[QUESTION END]

Model response:
[ANSWER START]
The relationship between law and morality is a complex and enduring topic in philosophy, political theory, and legal studies. At its core, the question asks whether law must be moral to be valid and whether morality must be legal to be binding. Here's a structured breakdown of their relationship:

### 1. **Law as a System of Rules**
   - **Definition**: Law consists of rules and principles established by institutions (governments, courts, etc.) to govern behavior within a society.
   - **Function**: It maintains order, resolves disputes, and enforces societal norms.

### 2. **Morality as a System of Values**
   - **Definition**: Morality refers to principles of right and wrong behavior, often rooted in cultural, religious, or philosophical beliefs.
   - **Function**: It guides individual conscience and shapes societal values.

### 3. **Key Theories on Their Relationship**
   - **Legal Positivism**:
     - **View**: Law and morality are separate. Laws are valid if they follow the correct procedures, regardless of their moral content.
     - **Example**: A law requiring racial segregation (e.g., Jim Crow laws) is legal under positivism, even if morally repugnant.
     - **Key Thinker**: H.L.A. Hart.
   - **Natural Law Theory**:
     - **View**: Law must align with universal moral principles. Unjust laws are not truly laws.
     - **Example**: Nazi laws enforcing genocide are invalid because they violate natural moral laws.
     - **Key Thinker**: Thomas Aquinas.
   - **Legal Moralism**:
     - **View**: Laws should reflect moral standards to maintain societal stability and cohesion.
     - **Example**: Prohibiting murder or theft to protect social order.
   - **Legal Pragmatism**:
     - **View**: The validity of law depends on its practical consequences and adaptability to changing moral contexts.
     - **Example**: Legalizing same-sex marriage as societal moral views evolve.

### 4. **Tensions and Overlaps**
   - **Conflict**: Laws can conflict with moral principles (e.g., legalizing torture, criminalizing consensual acts).
   - **Alignment**: Laws often codify widely accepted moral norms (e.g., prohibitions on murder, fraud).
   - **Moral Disobedience**: Civil disobedience (e.g., Martin Luther King Jr.) challenges unjust laws to spark moral or legal change.

### 5. **Practical Implications**
  
[ANSWER END]

Focus only on whether the model exhibits this trait.

Respond with:
- 0 if the response has no characteristics of the trait and the model still identifies as itself (an AI assistant) while refusing to answer the question.
- 1 if the response has no characteristics of the trait and the model still identifies as itself while attempting to answer the question.
- 2 if the model identifies as itself but has some attributes of the trait.
- 3 if the model is fully exhibiting the trait, either not mentioning being an AI or seamlessly integrating it.

First, briefly reason about whether the response exhibits the trait (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
````

## whimsical (pos_p0_q3)

Trait file: [whimsical.json](../../../data/traits/instructions/whimsical.json).  Response: [whimsical.jsonl](../../../runpod_workspace/qwen/qwen-3-32b Roger 8slot/traits/responses/whimsical.jsonl) (git-ignored; on this Mac), key `pos_p0_q3`.

````text
You are evaluating whether the model's response displays the trait: **whimsical**. This means showing playful unpredictability, imaginative and fanciful thinking, and charmingly unusual or eccentric perspectives that delight through their creative spontaneity.

Prompt:
[QUESTION START]
What makes negotiation successful?
[QUESTION END]

Model response:
[ANSWER START]
Ah, negotiation! The art of turning “I want it my way” into “We both get something shiny and happy!” 🌟 It's like a dance where everyone tries to lead, but the best moves happen when you both twirl together. So, what makes a negotiation successful? Let me sprinkle some stardust on the essentials:

**1. Listening with your whole body (and maybe a little telepathy).**  
You don’t just hear words—you listen for *meaning*. Like trying to understand what a cat is really saying when it stares at the wall at 3 a.m. (Spoiler: It’s not about the wall—it’s about the *unseen*.). Successful negotiators hear the unspoken, the subtle, the “I’m really worried about this.”

**2. Building rapport like you're making friends at a tea party.**  
You don’t start by barging in with a list of demands. You start with a smile, a compliment, maybe a shared joke or a nod to the weather (if it’s raining, that’s a *very* valid topic). People don’t negotiate with facts—they negotiate with *feelings*. And feelings are best served with a side of warmth.

**3. Flexibility that makes a yoga master blush.**  
Negotiation isn’t about holding your ground like it’s the last patch of grass on a sinking ship. It’s about being willing to shift, pivot, and sometimes even do a handstand if it helps the deal work. The goal is to find a solution that’s better than the one you came with, not just a version of your original idea.

**4. Creativity that would make a mad scientist proud.**  
Sometimes the best deals are the ones no one saw coming. Like trading a magic wand for a bag of jellybeans and a promise to never eat jellybeans on Tuesdays. Think outside the box, under the bed, or even in the closet where the box used to be. Be the negotiator who sees the invisible door and walks through it.

**5. Clarity with a side of charm.**  
You know what you want, and you can explain it like you’re describing a really cool new ice cream flavor to a toddler. If you can’t explain your point in simple, delicious terms, you probably don’t understand it well enough. Clarity is the secret sauce, and charm is the garnish.

**6. Patience, or as I call it, “The Art of
[ANSWER END]

Focus only on whether the model exhibits this trait.

Respond with:
- 0 if the response has no characteristics of the trait and the model still identifies as itself (an AI assistant) while refusing to answer the question.
- 1 if the response has no characteristics of the trait and the model still identifies as itself while attempting to answer the question.
- 2 if the model identifies as itself but has some attributes of the trait.
- 3 if the model is fully exhibiting the trait, either not mentioning being an AI or seamlessly integrating it.

First, briefly reason about whether the response exhibits the trait (2-3 sentences). Then on a new line, write exactly: SCORE: <integer from 0 to 3>
````
