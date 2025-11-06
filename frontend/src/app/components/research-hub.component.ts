import { Component, OnInit } from '@angular/core';
import { DataService } from '../data.service';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { NotebookViewComponent } from './notebook-view.component';

@Component({
  selector: 'app-research-hub',
  template: `
    <div *ngIf="!selectedNotebook; else notebookView">
      <div class="hub-container">
        <div class="notebook-list-section">
          <mat-card>
            <mat-card-header>
              <mat-card-title>My Notebooks</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <mat-list *ngIf="notebooks.length > 0; else emptyList">
                <mat-list-item *ngFor="let notebook of notebooks" (click)="selectNotebook(notebook)" class="notebook-item">
                  <mat-icon matListItemIcon>book</mat-icon>
                  <div matListItemTitle>{{ notebook.name }}</div>
                  <div matListItemLine>{{ notebook.description }}</div>
                  <button mat-icon-button (click)="deleteNotebook($event, notebook.id)">
                    <mat-icon color="warn">delete</mat-icon>
                  </button>
                </mat-list-item>
              </mat-list>
              <ng-template #emptyList>
                <p class="empty-message">No notebooks found. Create one to get started!</p>
              </ng-template>
            </mat-card-content>
          </mat-card>
        </div>
        <div class="create-notebook-section">
          <mat-card>
            <mat-card-header>
              <mat-card-title>Create New Notebook</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <form (ngSubmit)="createNotebook()">
                <mat-form-field appearance="outline">
                  <mat-label>Notebook Name</mat-label>
                  <input matInput [(ngModel)]="newNotebook.name" name="name" required>
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Description</mat-label>
                  <textarea matInput [(ngModel)]="newNotebook.description" name="description"></textarea>
                </mat-form-field>
                <button mat-flat-button color="primary" type="submit" [disabled]="!newNotebook.name">Create</button>
              </form>
            </mat-card-content>
          </mat-card>
        </div>
      </div>
    </div>

    <ng-template #notebookView>
      <app-notebook-view [notebook]="selectedNotebook" (onBack)="deselectNotebook()"></app-notebook-view>
    </ng-template>
  `,
  styles: [`
    .hub-container {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 2rem;
    }
    mat-card {
      height: 100%;
    }
    mat-form-field {
      width: 100%;
      margin-bottom: 1rem;
    }
    .empty-message {
      text-align: center;
      color: var(--text-secondary);
      padding: 2rem;
    }
    .notebook-item {
        cursor: pointer;
        border-bottom: 1px solid var(--border);
    }
    .notebook-item:hover {
        background-color: var(--hover);
    }
    .notebook-item:last-child {
      border-bottom: none;
    }
  `],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatIconModule,
    MatListModule,
    NotebookViewComponent
  ]
})
export class ResearchHubComponent implements OnInit {
  notebooks: any[] = [];
  newNotebook = { name: '', description: '' };
  selectedNotebook: any = null;

  constructor(private dataService: DataService) {}

  ngOnInit(): void {
    this.loadNotebooks();
  }

  loadNotebooks(): void {
    this.dataService.getNotebooks().subscribe(data => {
      this.notebooks = data;
    });
  }

  createNotebook(): void {
    if (this.newNotebook.name) {
      this.dataService.createNotebook(this.newNotebook).subscribe(() => {
        this.loadNotebooks();
        this.newNotebook = { name: '', description: '' };
      });
    }
  }

  deleteNotebook(event: MouseEvent, id: number): void {
    event.stopPropagation();
    if (confirm('Are you sure you want to delete this notebook and all its associated data?')) {
      this.dataService.deleteNotebook(id).subscribe(() => {
        this.loadNotebooks();
      });
    }
  }

  selectNotebook(notebook: any): void {
    this.selectedNotebook = notebook;
  }

  deselectNotebook(): void {
    this.selectedNotebook = null;
  }
}
