import { Component, OnInit } from '@angular/core';
import { DataService } from '../data.service';

interface LLMProvider {
  name: string;
  text_endpoint: string;
  image_endpoint: string;
  text_models: string[];
  image_models: string[];
  api_key_prefix: string;
}

interface LLMConfig {
  text_endpoint: string;
  text_model: string;
  text_api_keys: string[];
  image_endpoint: string;
  image_model: string;
  image_api_keys: string[];
}

interface Prompt {
  prompt_name: string;
  prompt_text: string;
}

@Component({
  selector: 'app-llm-settings',
  template: `
    <div class="llm-settings-container">
      <h2>Configuration LLM</h2>
      
      <div class="provider-selection">
        <label for="provider">Fournisseur LLM:</label>
        <select id="provider" [(ngModel)]="selectedProvider" (change)="onProviderChange()">
          <option value="">Sélectionnez un fournisseur</option>
          <option *ngFor="let provider of providers" [value]="provider.name">
            {{provider.name}}
          </option>
        </select>
      </div>

      <div *ngIf="selectedProvider" class="config-section">
        <h3>Configuration pour {{selectedProvider}}</h3>
        
        <div class="model-section">
          <h4>Traitement de texte</h4>
          <div class="form-group">
            <label for="textModel">Modèle texte:</label>
            <select id="textModel" [(ngModel)]="config.text_model">
              <option *ngFor="let model of currentProvider?.text_models" [value]="model">
                {{model}}
              </option>
            </select>
          </div>
          
          <div class="form-group">
            <label for="textApiKeys">Clés API texte (séparées par des virgules):</label>
            <input 
              type="text" 
              id="textApiKeys" 
              [(ngModel)]="textApiKeysInput"
              [placeholder]="'Ex: ' + currentProvider?.api_key_prefix + 'xxx,' + currentProvider?.api_key_prefix + 'yyy'"
            >
          </div>
        </div>

        <div class="model-section">
          <h4>Traitement d'images</h4>
          <div class="form-group">
            <label for="imageModel">Modèle image:</label>
            <select id="imageModel" [(ngModel)]="config.image_model">
              <option *ngFor="let model of currentProvider?.image_models" [value]="model">
                {{model}}
              </option>
            </select>
          </div>
          
          <div class="form-group">
            <label for="imageApiKeys">Clés API image (séparées par des virgules):</label>
            <input 
              type="text" 
              id="imageApiKeys" 
              [(ngModel)]="imageApiKeysInput"
              [placeholder]="'Ex: ' + currentProvider?.api_key_prefix + 'xxx,' + currentProvider?.api_key_prefix + 'yyy'"
            >
          </div>
        </div>

        <div class="actions">
          <button (click)="saveConfig()" [disabled]="!isConfigValid()">
            Sauvegarder la configuration
          </button>
          <button (click)="loadCurrentConfig()">
            Charger la configuration actuelle
          </button>
        </div>
      </div>

      <div *ngIf="message" class="message" [class.success]="isSuccess" [class.error]="!isSuccess">
        {{message}}
      </div>

      <div class="prompts-section">
        <h3>Prompts</h3>
        <div *ngFor="let prompt of prompts" class="prompt-editor">
          <label [for]="prompt.prompt_name">{{ prompt.prompt_name }}</label>
          <textarea [id]="prompt.prompt_name" [(ngModel)]="prompt.prompt_text" rows="10"></textarea>
          <button (click)="savePrompt(prompt)">Sauvegarder ce prompt</button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .llm-settings-container {
      max-width: 800px;
      margin: 20px auto;
      padding: 20px;
      border-radius: 8px;
      background: white;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }

    h2 {
      color: #333;
      margin-bottom: 20px;
    }

    h3 {
      color: #555;
      margin-top: 20px;
      margin-bottom: 15px;
    }

    h4 {
      color: #666;
      margin-top: 15px;
      margin-bottom: 10px;
    }

    .provider-selection {
      margin-bottom: 20px;
    }

    .config-section {
      border-top: 1px solid #eee;
      padding-top: 20px;
    }

    .model-section {
      background: #f9f9f9;
      padding: 15px;
      margin: 10px 0;
      border-radius: 5px;
    }

    .form-group {
      margin-bottom: 15px;
    }

    label {
      display: block;
      margin-bottom: 5px;
      font-weight: bold;
      color: #333;
    }

    select, input, textarea {
      width: 100%;
      padding: 8px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
    }

    select:focus, input:focus, textarea:focus {
      outline: none;
      border-color: #007bff;
      box-shadow: 0 0 0 2px rgba(0,123,255,0.25);
    }

    .actions {
      margin-top: 20px;
      display: flex;
      gap: 10px;
    }

    button {
      padding: 10px 20px;
      border: none;
      border-radius: 4px;
      font-size: 14px;
      cursor: pointer;
      transition: background-color 0.3s;
    }

    button:first-child {
      background-color: #007bff;
      color: white;
    }

    button:first-child:hover:not(:disabled) {
      background-color: #0056b3;
    }

    button:first-child:disabled {
      background-color: #ccc;
      cursor: not-allowed;
    }

    button:last-child {
      background-color: #6c757d;
      color: white;
    }

    button:last-child:hover {
      background-color: #545b62;
    }

    .message {
      margin-top: 15px;
      padding: 10px;
      border-radius: 4px;
    }

    .message.success {
      background-color: #d4edda;
      color: #155724;
      border: 1px solid #c3e6cb;
    }

    .message.error {
      background-color: #f8d7da;
      color: #721c24;
      border: 1px solid #f5c6cb;
    }

    .prompts-section {
      margin-top: 30px;
      border-top: 1px solid #eee;
      padding-top: 20px;
    }

    .prompt-editor {
      margin-bottom: 20px;
    }

    .prompt-editor textarea {
      height: 150px;
      resize: vertical;
    }

    .prompt-editor button {
      margin-top: 10px;
      background-color: #28a745;
      color: white;
    }

    .prompt-editor button:hover {
      background-color: #218838;
    }
  `]
})
export class LlmSettingsComponent implements OnInit {
  providers: LLMProvider[] = [];
  selectedProvider: string = '';
  currentProvider: LLMProvider | null = null;
  config: LLMConfig = {
    text_endpoint: '',
    text_model: '',
    text_api_keys: [],
    image_endpoint: '',
    image_model: '',
    image_api_keys: []
  };
  textApiKeysInput: string = '';
  imageApiKeysInput: string = '';
  message: string = '';
  isSuccess: boolean = false;
  prompts: Prompt[] = [];

  constructor(private dataService: DataService) {}

  ngOnInit() {
    this.loadProviders();
    this.loadCurrentConfig();
    this.loadPrompts();
  }

  async loadProviders() {
    try {
      const response = await this.dataService.getLLMProviders();
      this.providers = response.providers;
    } catch (error) {
      this.showMessage('Erreur lors du chargement des fournisseurs', false);
    }
  }

  async loadCurrentConfig() {
    try {
      const currentConfig = await this.dataService.getCurrentLLMConfig();
      this.config = currentConfig;
      
      // Convert arrays to comma-separated strings for display
      this.textApiKeysInput = currentConfig.text_api_keys.join(',');
      this.imageApiKeysInput = currentConfig.image_api_keys.join(',');
      
      // Try to detect current provider
      const provider = this.providers.find(p => 
        p.text_endpoint === currentConfig.text_endpoint
      );
      if (provider) {
        this.selectedProvider = provider.name;
        this.currentProvider = provider;
      }
    } catch (error) {
      this.showMessage('Erreur lors du chargement de la configuration actuelle', false);
    }
  }

  onProviderChange() {
    this.currentProvider = this.providers.find(p => p.name === this.selectedProvider) || null;
    if (this.currentProvider) {
      this.config.text_endpoint = this.currentProvider.text_endpoint;
      this.config.image_endpoint = this.currentProvider.image_endpoint;
      this.config.text_model = this.currentProvider.text_models[0] || '';
      this.config.image_model = this.currentProvider.image_models[0] || '';
      
      // Set default API keys for Ollama
      if (this.selectedProvider === 'Ollama') {
        this.textApiKeysInput = 'ollama';
        this.imageApiKeysInput = 'ollama';
      } else {
        this.textApiKeysInput = '';
        this.imageApiKeysInput = '';
      }
    }
  }

  isConfigValid(): boolean {
    return !!(
      this.selectedProvider &&
      this.config.text_model &&
      this.config.image_model &&
      this.textApiKeysInput.trim() &&
      this.imageApiKeysInput.trim()
    );
  }

  async saveConfig() {
    if (!this.isConfigValid()) {
      this.showMessage('Veuillez remplir tous les champs', false);
      return;
    }

    // Convert comma-separated strings to arrays and format as JSON strings
    const textKeys = this.textApiKeysInput.split(',').map(key => key.trim()).filter(key => key);
    const imageKeys = this.imageApiKeysInput.split(',').map(key => key.trim()).filter(key => key);

    const configData = {
      text_endpoint: this.config.text_endpoint,
      text_model: this.config.text_model,
      text_api_keys: JSON.stringify(textKeys),
      image_endpoint: this.config.image_endpoint,
      image_model: this.config.image_model,
      image_api_keys: JSON.stringify(imageKeys)
    };

    try {
      await this.dataService.updateLLMConfig(configData);
      this.showMessage('Configuration sauvegardée avec succès!', true);
    } catch (error) {
      this.showMessage('Erreur lors de la sauvegarde de la configuration', false);
    }
  }

  async loadPrompts() {
    try {
      this.prompts = await this.dataService.getPrompts();
    } catch (error) {
      this.showMessage('Erreur lors du chargement des prompts', false);
    }
  }

  async savePrompt(prompt: Prompt) {
    try {
      await this.dataService.updatePrompt(prompt);
      this.showMessage('Prompt sauvegardé avec succès!', true);
    } catch (error) {
      this.showMessage('Erreur lors de la sauvegarde du prompt', false);
    }
  }

  showMessage(msg: string, success: boolean) {
    this.message = msg;
    this.isSuccess = success;
    setTimeout(() => {
      this.message = '';
    }, 5000);
  }
}