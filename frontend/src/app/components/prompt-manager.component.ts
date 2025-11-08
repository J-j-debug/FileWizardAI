
import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatTooltipModule } from '@angular/material/tooltip';

import { CustomPrompt } from '../models';

export interface PromptManagerData {
  prompts: CustomPrompt[];
  defaultPromptContent: string;
}

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
    MatIconModule,
    MatListModule,
    MatTooltipModule
  ],
  template: `
    <div class="prompt-manager-container">
      <h2 mat-dialog-title>Gérer les Prompts Personnalisés</h2>
      <mat-dialog-content class="dialog-content">
        <div class="prompts-list-section">
          <h3>Prompts Sauvegardés</h3>
          <mat-list>
            <mat-list-item *ngFor="let prompt of customPrompts; let i = index">
              <span matListItemTitle>{{ prompt.title }}</span>
              <div matListItemMeta>
                <button mat-icon-button (click)="editPrompt(i)" matTooltip="Modifier le prompt">
                  <mat-icon>edit</mat-icon>
                </button>
                <button mat-icon-button color="warn" (click)="deletePrompt(i)" matTooltip="Supprimer le prompt">
                  <mat-icon>delete</mat-icon>
                </button>
              </div>
            </mat-list-item>
          </mat-list>
          <p *ngIf="customPrompts.length === 0" class="no-prompts">Aucun prompt personnalisé.</p>
        </div>
        <div class="prompt-edit-section">
          <h3>{{ editingIndex === null ? 'Créer un nouveau prompt' : 'Modifier le prompt' }}</h3>
          <mat-form-field appearance="outline">
            <mat-label>Titre</mat-label>
            <input matInput [(ngModel)]="currentPrompt.title" placeholder="Ex: Thèse, Travail, etc.">
          </mat-form-field>
          <mat-form-field appearance="outline" class="prompt-content-field">
            <mat-label>Contenu du Prompt</mat-label>
            <textarea matInput cdkTextareaAutosize cdkAutosizeMinRows="8" [(ngModel)]="currentPrompt.content"></textarea>
          </mat-form-field>
          <div class="edit-actions">
            <button mat-stroked-button (click)="startNewPrompt()">
                <mat-icon>add</mat-icon> Nouveau
            </button>
             <button mat-stroked-button (click)="restoreDefault()" matTooltip="Copier le contenu du prompt par défaut dans l'éditeur">
                <mat-icon>restart_alt</mat-icon> Rétablir par défaut
            </button>
          </div>
        </div>
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-button (click)="onCancel()">Annuler</button>
        <button mat-flat-button color="primary" (click)="onSave()" [disabled]="!currentPrompt.title || !currentPrompt.content">
            <mat-icon>save</mat-icon>
            {{ editingIndex === null ? 'Sauvegarder' : 'Mettre à jour' }}
        </button>
      </mat-dialog-actions>
    </div>
  `,
  styles: [`
    .prompt-manager-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      max-height: 80vh;
    }
    .dialog-content {
      display: grid;
      grid-template-columns: 1fr 2fr;
      gap: 2rem;
      padding: 1rem;
      overflow-y: auto;
    }
    .prompts-list-section {
      border-right: 1px solid var(--border);
      padding-right: 2rem;
    }
    .prompt-edit-section {
      display: flex;
      flex-direction: column;
    }
    .prompt-content-field {
      flex-grow: 1;
    }
    .edit-actions {
      display: flex;
      gap: 0.5rem;
      margin-top: 1rem;
    }
    mat-form-field {
      width: 100%;
    }
    .no-prompts {
      color: var(--text-secondary);
      font-style: italic;
    }
  `]
})
export class PromptManagerComponent {
  customPrompts: CustomPrompt[];
  currentPrompt: CustomPrompt = { title: '', content: '' };
  editingIndex: number | null = null;
  defaultPromptContent: string;

  constructor(
    public dialogRef: MatDialogRef<PromptManagerComponent>,
    @Inject(MAT_DIALOG_DATA) public data: PromptManagerData
  ) {
    // We only manage non-default prompts
    this.customPrompts = data.prompts.filter(p => p.title !== 'Default Prompt');
    this.defaultPromptContent = data.defaultPromptContent;
    this.startNewPrompt();
  }

  startNewPrompt(): void {
    this.editingIndex = null;
    this.currentPrompt = { title: '', content: this.defaultPromptContent };
  }

  editPrompt(index: number): void {
    this.editingIndex = index;
    // Create a copy for editing to not modify the original until save
    this.currentPrompt = { ...this.customPrompts[index] };
  }

  deletePrompt(index: number): void {
    this.customPrompts.splice(index, 1);
    if (this.editingIndex === index) {
      this.startNewPrompt();
    }
  }

  restoreDefault(): void {
    this.currentPrompt.content = this.defaultPromptContent;
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSave(): void {
    if (this.editingIndex === null) {
      // Add new prompt
      this.customPrompts.push(this.currentPrompt);
    } else {
      // Update existing prompt
      this.customPrompts[this.editingIndex] = this.currentPrompt;
    }
    this.dialogRef.close(this.customPrompts);
  }
}
