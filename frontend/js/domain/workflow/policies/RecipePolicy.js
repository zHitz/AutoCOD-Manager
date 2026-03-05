import { DomainError } from '../errors/DomainError.js';

export class RecipePolicy {
    static validate(recipe) {
        if (!recipe.name || recipe.name.trim() === '') {
            throw new DomainError('INVALID_NAME', 'Recipe name cannot be empty');
        }

        if (!Array.isArray(recipe.steps) || recipe.steps.length === 0) {
            throw new DomainError('NO_STEPS', 'Recipe must have at least one step');
        }

        recipe.steps.forEach((step, index) => {
            this.validateStep(step, index);
        });

        return true;
    }

    static validateStep(step, index) {
        if (!step.function_id) {
            throw new DomainError('INVALID_STEP', `Step ${index + 1} is missing a function_id`);
        }

        if (!step.config || typeof step.config !== 'object') {
            throw new DomainError('INVALID_STEP_CONFIG', `Step ${index + 1} has an invalid config`);
        }
    }
}
