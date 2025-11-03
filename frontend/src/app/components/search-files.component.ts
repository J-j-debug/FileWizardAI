import { Component, Input } from '@angular/core';
import { HttpParams } from "@angular/common/http";
import { DataService } from "../data.service";

@Component({
  selector: 'app-search-files',
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
      <button mat-raised-button (click)="searchFiles()" class="search-button">Search</button>
    </div>
    <div class="spinner-container" *ngIf="isLoading">
        <mat-spinner></mat-spinner>
    </div>
    <div *ngIf="ragResult" class="results-container">
      <h3>Response:</h3>
      <p>{{ ragResult.response }}</p>

      <h4>Sources:</h4>
      <ul>
        <li *ngFor="let source of ragResult.sources">{{ source.file_path }} (Page: {{ source.page }})</li>
      </ul>
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
    .spinner-container {
      display: flex;
      justify-content: center;
      align-items: center;
      margin-top: 20px;
    }
    .results-container {
      margin-top: 20px;
    }
  `]
})
export class SearchFilesComponent {
  searchQuery: string = "";
  ragResult: any;
  isLoading: boolean = false;
  selectedCollection: string = "file_embeddings"; // Default collection
  collections = [
    { value: "file_embeddings", viewValue: "Recherche Standard" },
    { value: "file_embeddings_unstructured", viewValue: "Recherche Avancée (Unstructured)" }
  ];
  @Input() rootPath: string = "";
  @Input() isRecursive: boolean = false;
  @Input() filesExts: string[] = [];

  constructor(private dataService: DataService) {
  }

  searchFiles(): void {
    this.ragResult = null;
    this.isLoading = true;
    let params = new HttpParams();
    params = params.set("query", this.searchQuery);
    params = params.set("collection_name", this.selectedCollection); // Add the selected collection
    this.dataService
      .ragSearch(params)
      .subscribe((data: any) => {
        this.ragResult = data;
        this.isLoading = false;
      })
  }
}
