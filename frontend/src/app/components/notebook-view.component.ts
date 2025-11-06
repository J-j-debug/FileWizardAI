import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { DataService } from '../data.service';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { HttpParams } from '@angular/common/http';

@Component({
  selector: 'app-notebook-view',
  template: `
    <div class="notebook-view-container">
      <button mat-stroked-button (click)="onBack.emit()">
        <mat-icon>arrow_back</mat-icon>
        Back to Notebooks
      </button>

      <mat-card class="notebook-header">
        <h1>{{ notebook.name }}</h1>
        <p>{{ notebook.description }}</p>
      </mat-card>

      <div class="notebook-content">
        <div class="files-section">
          <mat-card>
            <mat-card-header>
              <mat-card-title>Notebook Files</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              <button mat-flat-button color="primary" (click)="addFiles()">Add Files</button>
              <mat-list *ngIf="files.length > 0">
                <mat-list-item *ngFor="let file of files">
                  <mat-icon matListItemIcon>insert_drive_file</mat-icon>
                  <div matListItemTitle>{{ file.split('/').pop() }}</div>
                  <div matListItemLine>{{ file }}</div>
                </mat-list-item>
              </mat-list>
              <button mat-flat-button color="accent" (click)="indexFiles()" [disabled]="!files.length || isLoading">
                <mat-icon>api</mat-icon>
                Index Files
              </button>
            </mat-card-content>
          </mat-card>
        </div>
        <div class="search-section">
          <mat-card>
            <mat-card-header>
              <mat-card-title>Search in Notebook</mat-card-title>
            </mat-card-header>
            <mat-card-content>
                <mat-form-field appearance="outline">
                    <mat-label>Search Query</mat-label>
                    <textarea matInput [(ngModel)]="searchQuery" placeholder="Ask a question..."></textarea>
                </mat-form-field>
                <mat-checkbox [(ngModel)]="useAdvancedIndexing">Use Advanced Search</mat-checkbox>
                <button mat-flat-button color="primary" (click)="search()" [disabled]="!searchQuery || isLoading">
                    Search
                </button>
                <mat-spinner *ngIf="isLoading" [diameter]="30"></mat-spinner>
                <div *ngIf="searchResults">
                    <h3>Main Answer</h3>
                    <p>{{ searchResults.main_response.response }}</p>
                    <p>Source: {{ searchResults.main_response.source.file_path }}</p>
                    <h3 *ngIf="searchResults.other_relevant_passages.length > 0">Other Relevant Passages</h3>
                    <ul>
                        <li *ngFor="let passage of searchResults.other_relevant_passages">
                            <p>{{ passage.document }}</p>
                            <p>Source: {{ passage.metadata.file_path }}</p>
                        </li>
                    </ul>
                </div>
            </mat-card-content>
          </mat-card>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .notebook-view-container { padding: 1rem; }
    .notebook-header { margin: 1rem 0; }
    .notebook-content { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
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
    MatCheckboxModule,
    MatProgressSpinnerModule
  ]
})
export class NotebookViewComponent implements OnInit {
  @Input() notebook: any;
  @Output() onBack = new EventEmitter<void>();

  files: string[] = [];
  searchQuery: string = '';
  useAdvancedIndexing: boolean = false;
  isLoading: boolean = false;
  searchResults: any = null;

  constructor(private dataService: DataService) {}

  ngOnInit(): void {
    this.loadFiles();
  }

  loadFiles(): void {
    this.dataService.getNotebookFiles(this.notebook.id).subscribe(data => {
      this.files = data.file_paths;
    });
  }

  addFiles(): void {
    // This would ideally open a file picker. For now, we'll simulate adding a file.
    const newFile = prompt("Enter the full path of the file to add:");
    if (newFile) {
        this.dataService.addFilesToNotebook(this.notebook.id, [newFile]).subscribe(() => {
            this.loadFiles();
        });
    }
  }

  indexFiles(): void {
    this.isLoading = true;
    this.dataService.indexNotebookFiles(this.notebook.id, this.files, this.useAdvancedIndexing).subscribe(() => {
      this.isLoading = false;
      alert('Files indexed successfully!');
    }, () => this.isLoading = false);
  }

  search(): void {
    this.isLoading = true;
    this.searchResults = null;
    let params = new HttpParams().set('query', this.searchQuery).set('use_advanced_indexing', this.useAdvancedIndexing);
    this.dataService.searchInNotebook(this.notebook.id, params).subscribe(results => {
      this.searchResults = results;
      this.isLoading = false;
    }, () => this.isLoading = false);
  }
}
