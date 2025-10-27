// Random Prompt Generator for Pearl Pixel Salon
// FIXED #18: Simple prompts without style descriptors
const STARTER_PROMPTS = [
    "A cute frog with big blue eyes",
    "A robotic samurai warrior with metallic armor and red eyes",
    "A brave knight with silver armor",
    "A wizard with a long white beard",
    "A ninja with a black mask",
    "A dragon with golden scales",
    "A pirate with an eyepatch and tricorn hat",
    "An astronaut with a glass helmet",
    "A mermaid with flowing green hair",
    "A firefighter with yellow helmet and axe",
    "A chef with white hat and wooden spoon",
    "A detective with brown trench coat and magnifying glass",
    "A vampire with pale skin and red cape",
    "A witch with pointy hat and broom",
    "An elf with pointy ears and bow",
    "A zombie with tattered clothes",
    "A fairy with translucent wings",
    "A cyborg with glowing circuits",
    "A werewolf with sharp claws",
    "A ghost with flowing white sheets"
];

function getRandomPrompt() {
    const index = Math.floor(Math.random() * STARTER_PROMPTS.length);
    return STARTER_PROMPTS[index]; // FIXED #18: No style keywords appended
}

// Export for use in main app
window.StarterPrompts = {
    getRandomPrompt,
    all: STARTER_PROMPTS
};

