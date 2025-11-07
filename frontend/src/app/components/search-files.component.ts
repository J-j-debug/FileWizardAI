import { Component, Input } from '@angular/core';
import { HttpParams } from "@angular/common/http";
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DataService } from "../data.service";

// Angular Material Modules
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-search-files',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="search-controls">
      <mat-form-field class="search-input">
        <mat-label>Search text</mat-label>
        <textarea matInput placeholder="Ask a question about your documents" [(ngModel)]="searchQuery"></textarea>
      </mat-form-field>
      <mat-form-field class="collection-select">
        <mat-label>Search In</mat-label>
        <mat-select [(ngModel)]="selectedCollection">
          <mat-option *ngFor="let collection of collections" [value]="collection.value">
            {{ collection.viewValue }}
          </mat-option>
        </mat-select>
      </mat-form-field>
      <mat-form-field class="top-k-input">
        <mat-label>Top K</mat-label>
        <input matInput type="number" [(ngModel)]="topK" min="1" max="20">
      </mat-form-field>
      <button mat-raised-button (click)="searchFiles()" class="search-button">Search</button>
      <button mat-icon-button (click)="toggleAdvancedSettings()" matTooltip="Advanced Search Settings">
        <mat-icon>settings</mat-icon>
      </button>
    </div>

    <div *ngIf="showAdvancedSettings" class="advanced-settings-panel">
      <h4>Prompt de Synthèse</h4>
      <mat-form-field class="prompt-select">
        <mat-label>Modèle de Prompt</mat-label>
        <mat-select [(ngModel)]="selectedPrompt" (selectionChange)="onPromptSelectionChange()">
          <mat-option *ngFor="let prompt of promptTemplates" [value]="prompt.id">
            {{ prompt.name }}
          </mat-option>
        </mat-select>
      </mat-form-field>
      <mat-form-field class="prompt-textarea">
        <mat-label>Contenu du Prompt</mat-label>
        <textarea matInput
                  [readonly]="selectedPrompt !== 'custom'"
                  [(ngModel)]="currentPromptContent"
                  rows="6"></textarea>
      </mat-form-field>
      <button mat-stroked-button *ngIf="selectedPrompt === 'custom'" (click)="saveCustomPrompt()">
        Sauvegarder le prompt personnalisé
      </button>
    </div>

    <div class="spinner-container" *ngIf="isLoading">
        <mat-spinner></mat-spinner>
    </div>
    <div *ngIf="ragResult" class="results-container">
      <h3>Réponse Principale:</h3>
      <p>{{ ragResult.main_response.response }}</p>
      <div *ngIf="ragResult.main_response.source" class="source-citation">
        <strong>Source:</strong>
        <a [href]="'http://localhost:8000/download?encoded_path=' + encodeFilePath(ragResult.main_response.source.file_path)" target="_blank">
          {{ ragResult.main_response.source.file_path }}
        </a>
        (Page: {{ ragResult.main_response.source.page_number }})
      </div>

      <h4>Autres Passages Pertinents:</h4>
      <ul *ngIf="ragResult.other_relevant_passages && ragResult.other_relevant_passages.length > 0; else noOtherPassages">
        <li *ngFor="let passage of ragResult.other_relevant_passages">
          <p class="passage-content">"{{ passage.document }}"</p>
          <div class="source-citation">
            <strong>Source:</strong>
            <a [href]="'http://localhost:8000/download?encoded_path=' + encodeFilePath(passage.metadata.file_path)" target="_blank">
              {{ passage.metadata.file_path }}
            </a>
            (Page: {{ passage.metadata.page_number }})
          </div>
        </li>
      </ul>
      <ng-template #noOtherPassages>
        <p>Aucun autre passage pertinent trouvé.</p>
      </ng-template>
    </div>
  `,
  styles: [`
    .search-controls {
      display: flex;
      align-items: center;
      gap: 1rem;
      width: 100%;
    }
    .search-input {
      flex-grow: 1;
    }
    .collection-select {
      width: 250px; /* Adjust as needed */
    }
    .top-k-input {
      width: 80px;
    }
    .spinner-container {
      display: flex;
      justify-content: center;
      align-items: center;
      margin-top: 20px;
    }
    .results-container {
      margin-top: 20px;
    }
    .passage-content {
      font-style: italic;
      padding-left: 1rem;
      border-left: 2px solid #ccc;
    }
    .source-citation {
      font-size: 0.9em;
      color: #555;
    }
    .advanced-settings-panel {
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 1rem;
      margin-top: 1rem;
      background-color: #f9f9f9;
    }
    .prompt-select {
      width: 100%;
    }
    .prompt-textarea {
      width: 100%;
      margin-top: 1rem;
    }
  `]
})
export class SearchFilesComponent {
  searchQuery: string = "";
  ragResult: any;
  isLoading: boolean = false;
  selectedCollection: string = "file_embeddings"; // Default collection
  topK: number = 5;
  collections = [
    { value: "file_embeddings", viewValue: "Recherche Standard" },
    { value: "file_embeddings_unstructured", viewValue: "Recherche Avancée (Unstructured)" }
  ];

  // Advanced settings
  showAdvancedSettings: boolean = false;
  selectedPrompt: string = 'default';
  currentPromptContent: string = '';
  promptTemplates = [
    { id: 'default', name: 'Prompt par Défaut (Extraction Directe)', content: `
        You are a search assistant. Your task is to find and extract the most relevant passages from the provided text to answer the user's query.
        Do not synthesize or generate new answers. Your response should consist only of direct quotes from the text.
        If no relevant passages are found, simply state that.

        **Query:** {query}

        **Context:**
        ---
        {context}
        ---

        **Citations:**
    `.trim() },
    { id: 'summary', name: 'Prompt de Synthèse', content: `
        Réponds à la question en te basant sur le texte fourni. Si le texte ne contient pas de réponse directe, résume les informations les plus importantes qu'il contient en rapport avec la question.

        **Question:** {query}

        **Texte:**
        ---
        {context}
        ---
    `.trim() },
    { id: 'custom', name: 'Prompt Personnalisé', content: '' }
  ];

  @Input() rootPath: string = "";
  @Input() isRecursive: boolean = false;
  @Input() filesExts: string[] = [];

  constructor(private dataService: DataService) {
    this.loadCustomPrompt();
    this.onPromptSelectionChange();
  }

  encodeFilePath(path: string): string {
    return btoa(path);
  }

  toggleAdvancedSettings() {
    this.showAdvancedSettings = !this.showAdvancedSettings;
  }

  onPromptSelectionChange() {
    const selectedTemplate = this.promptTemplates.find(p => p.id === this.selectedPrompt);
    if (selectedTemplate) {
      this.currentPromptContent = selectedTemplate.content;
    }
  }

  loadCustomPrompt() {
    const savedPrompt = localStorage.getItem('customRagPrompt');
    const customPromptTemplate = this.promptTemplates.find(p => p.id === 'custom');
    if (customPromptTemplate && savedPrompt) {
      customPromptTemplate.content = savedPrompt;
    } else if (customPromptTemplate) {
      customPromptTemplate.content = 'Écrivez votre prompt personnalisé ici. Utilisez {query} et {context} comme variables.';
    }
  }

  saveCustomPrompt() {
    localStorage.setItem('customRagPrompt', this.currentPromptContent);
    const customPromptTemplate = this.promptTemplates.find(p => p.id === 'custom');
    if (customPromptTemplate) {
      customPromptTemplate.content = this.currentPromptContent;
    }
    // You might want to add a visual confirmation, like a snackbar
    console.log("Prompt personnalisé sauvegardé !");
  }

  searchFiles(): void {
    this.ragResult = null;
    this.isLoading = true;
    let params = new HttpParams();
    params = params.set("query", this.searchQuery);
    params = params.set("collection_name", this.selectedCollection);
    params = params.set("top_k", this.topK.toString());

    // Add the selected prompt content to the request
    if (this.currentPromptContent) {
      params = params.set("prompt_template", this.currentPromptContent);
    }

    this.dataService
      .ragSearch(params)
      .subscribe((data: any) => {
        this.ragResult = data;
        this.isLoading = false;
      })
  }
}
