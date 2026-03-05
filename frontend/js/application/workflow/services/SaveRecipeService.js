import { Result } from '../../../shared/result/Result.js';
import { RecipePolicy } from '../../../domain/workflow/policies/RecipePolicy.js';

export class SaveRecipeService {
    constructor({ workflowRepo }) {
        this.workflowRepo = workflowRepo;
    }

    async execute(command) {
        try {
            const recipeDto = {
                id: command.recipeId,
                name: command.name,
                steps: command.steps,
                icon: command.icon || '📝',
                description: command.description || ''
            };

            // 1. Validate domain rules
            RecipePolicy.validate(recipeDto);

            // 2. Persist
            const result = await this.workflowRepo.saveRecipe(recipeDto);

            if (!result.ok) {
                return Result.fail(result.error);
            }

            return Result.ok(result.data);

        } catch (error) {
            return Result.fail(error);
        }
    }
}
