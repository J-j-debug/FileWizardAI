import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { CustomPrompt } from '../models';

@Component({
  selector: 'app-prompt-manager',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatListModule,
    MatIconModule,
    MatTooltipModule
  ],
  template: `
    <div class="prompt-manager-container">
      <h1 mat-dialog-title>Gestionnaire de Prompts Personnalisés</h1>
      <div mat-dialog-content class="dialog-content">
        <div class="prompts-list">
          <mat-selection-list #promptList [multiple]="false" (selectionChange)="onPromptSelected($event)">
            <mat-list-option *ngFor="let prompt of prompts; let i = index" [value]="prompt" [selected]="prompt === selectedPrompt">
              <div class="prompt-item">
                <span class="prompt-title">{{ prompt.title }}</span>
                <div class="prompt-actions">
                  <button mat-icon-button (click)="editPrompt(prompt, $event)" [disabled]="isDefaultPrompt(prompt)" matTooltip="Modifier le prompt">
                    <mat-icon>edit</mat-icon>
                  </button>
                  <button mat-icon-button (click)="deletePrompt(prompt, $event)" [disabled]="isDefaultPrompt(prompt)" color="warn" matTooltip="Supprimer le prompt">
                    <mat-icon>delete</mat-icon>
                  </button>
                </div>
              </div>
            </mat-list-option>
          </mat-selection-list>
        </div>
        <div class="prompt-editor">
          <mat-form-field appearance="outline">
            <mat-label>Titre du Prompt</mat-label>
            <input matInput [(ngModel)]="editablePrompt.title" placeholder="Ex: Résumé pour un rapport" [disabled]="isDefaultPrompt(selectedPrompt)">
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Contenu du Prompt</mat-label>
            <textarea matInput cdkTextareaAutosize cdkAutosizeMinRows="5" [(ngModel)]="editablePrompt.content" [disabled]="isDefaultPrompt(selectedPrompt)"></textarea>
          </mat-form-field>
           <p *ngIf="isDefaultPrompt(selectedPrompt)" class="default-prompt-info">
            <mat-icon>info</mat-icon>
            Le prompt par défaut ne peut pas être modifié. Cliquez sur 'Créer un nouveau prompt' pour commencer.
          </p>
        </div>
      </div>
      <div mat-dialog-actions class="dialog-actions">
        <button mat-stroked-button (click)="createNewPrompt()">
          <mat-icon>add</mat-icon>
          Créer un nouveau prompt
        </button>
        <div>
          <button mat-button (click)="onCancel()">Annuler</button>
          <button mat-flat-button color="primary" (click)="onSave()" [disabled]="!isChanged() || isDefaultPrompt(selectedPrompt)">
            <mat-icon>save</mat-icon>
            Sauvegarder les changements
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .prompt-manager-container {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .dialog-content {
      flex-grow: 1;
      display: grid;
      grid-template-columns: 1fr 2fr;
      gap: 24px;
      overflow-y: auto;
    }
    .prompts-list {
      border-right: 1px solid #e0e0e0;
      padding-right: 16px;
    }
    .prompt-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;
    }
    .prompt-title {
      flex-grow: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .prompt-actions {
      display: flex;
      gap: 8px;
    }
    .prompt-editor {
      display: flex;
      flex-direction: column;
    }
    .prompt-editor mat-form-field {
      width: 100%;
      margin-bottom: 16px;
    }
    .dialog-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 16px;
      border-top: 1px solid #e0e0e0;
    }
    .default-prompt-info {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.9em;
      color: #666;
      background-color: #f5f5f5;
      padding: 8px;
      border-radius: 4px;
    }
  `]
})
export class PromptManagerComponent {
  prompts: CustomPrompt[];
  selectedPrompt: CustomPrompt | null = null;
  editablePrompt: CustomPrompt = { title: '', content: '' };
  originalPrompt: CustomPrompt | null = null;
  defaultPrompt: CustomPrompt;

  constructor(
    public dialogRef: MatDialogRef<PromptManagerComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {
    this.prompts = [...data.prompts]; // Create a local copy
    this.defaultPrompt = data.defaultPrompt;
  }

  onPromptSelected(event: any): void {
    this.selectedPrompt = event.options[0].value;
    if (this.selectedPrompt) {
      this.originalPrompt = JSON.parse(JSON.stringify(this.selectedPrompt)); // Deep copy
      this.editablePrompt = { ...this.selectedPrompt };
    }
  }

  isDefaultPrompt(prompt: CustomPrompt | null): boolean {
    return prompt === this.defaultPrompt;
  }

  isChanged(): boolean {
    if (!this.selectedPrompt || !this.originalPrompt) return false;
    return this.editablePrompt.title !== this.originalPrompt.title || this.editablePrompt.content !== this.originalPrompt.content;
  }

  editPrompt(prompt: CustomPrompt, event: MouseEvent): void {
    event.stopPropagation();
    this.selectedPrompt = prompt;
    this.originalPrompt = JSON.parse(JSON.stringify(this.selectedPrompt));
    this.editablePrompt = { ...this.selectedPrompt };
  }

  deletePrompt(promptToDelete: CustomPrompt, event: MouseEvent): void {
    event.stopPropagation();
    if (this.isDefaultPrompt(promptToDelete)) return;
    this.prompts = this.prompts.filter(p => p !== promptToDelete);
    if (this.selectedPrompt === promptToDelete) {
      this.selectedPrompt = null;
      this.editablePrompt = { title: '', content: '' };
    }
    // Save immediately on delete
    this.dialogRef.close(this.prompts.filter(p => !this.isDefaultPrompt(p)));
  }

  createNewPrompt(): void {
    const newPrompt: CustomPrompt = { title: 'Nouveau Prompt', content: this.defaultPrompt.content };
    this.prompts.push(newPrompt);
    this.selectedPrompt = newPrompt;
    this.originalPrompt = JSON.parse(JSON.stringify(this.selectedPrompt));
    this.editablePrompt = { ...this.selectedPrompt };
  }

  onSave(): void {
    if (this.selectedPrompt && this.isChanged()) {
      const index = this.prompts.findIndex(p => p === this.selectedPrompt);
      if (index > -1) {
        this.prompts[index] = this.editablePrompt;
      }
    }
    // Return only custom prompts
    this.dialogRef.close(this.prompts.filter(p => !this.isDefaultPrompt(p)));
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
